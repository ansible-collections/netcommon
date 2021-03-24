#
# (c) 2018 Red Hat Inc.
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
#
from __future__ import absolute_import, division, print_function

__metaclass__ = type

import os
import time
import re

from ansible.errors import AnsibleError
from ansible.module_utils._text import to_text, to_bytes
from ansible.module_utils.six.moves.urllib.parse import urlsplit
from ansible.plugins.action.normal import ActionModule as _ActionModule
from ansible.utils.display import Display
from ansible.module_utils.six import PY3
from ansible.module_utils.connection import Connection

display = Display()

PRIVATE_KEYS_RE = re.compile("__.+__")
DEXEC_PREFIX = "ANSIBLE_NETWORK_IMPORT_MODULES:"


class ActionModule(_ActionModule):
    def run(self, task_vars=None):
        config_module = hasattr(self, "_config_module") and self._config_module
        if config_module and self._task.args.get("src"):
            try:
                self._handle_src_option()
            except AnsibleError as exc:
                return dict(failed=True, msg=to_text(exc))

        host = task_vars["ansible_host"]
        dexec_eligible = self._check_dexec_eligibility(host)

        # attempt to run using dexec
        if dexec_eligible:
            # find and load the module
            filename, module = self._find_load_module()
            display.vvvv(
                "{prefix} found {action}  at {fname}".format(
                    prefix=DEXEC_PREFIX,
                    action=self._task.action,
                    fname=filename,
                ),
                host,
            )
            # not using AnsibleModule, return to normal run (eg eos_bgp)
            if getattr(module, "AnsibleModule", None):
                # patch and update the module
                self._patch_update_module(module, task_vars)
                display.vvvv(
                    "{prefix} running {module}".format(
                        prefix=DEXEC_PREFIX, module=self._task.action
                    ),
                    host,
                )
                # execute the module, collect result
                result = self._exec_module(module)
                display.vvvv(
                    "{prefix} complete".format(prefix=DEXEC_PREFIX), host
                )
                display.vvvvv(
                    "{prefix} Result: {result}".format(
                        prefix=DEXEC_PREFIX, result=result
                    ),
                    host,
                )

            else:
                dexec_eligible = False
                display.vvvv(
                    "{prefix} {module} doesn't support direct execution, disabled".format(
                        prefix=DEXEC_PREFIX, module=self._task.action
                    ),
                    host,
                )

        if not dexec_eligible:
            result = super(ActionModule, self).run(task_vars=task_vars)

        if (
            config_module
            and self._task.args.get("backup")
            and not result.get("failed")
        ):
            self._handle_backup_option(result, task_vars)

        return result

    def _handle_backup_option(self, result, task_vars):

        filename = None
        backup_path = None

        try:
            content = self._sanitize_contents(
                contents=result["__backup__"],
                filters=result["__non_config_lines__"],
            )
        except KeyError:
            raise AnsibleError("Failed while reading configuration backup")

        backup_options = self._task.args.get("backup_options")
        if backup_options:
            filename = backup_options.get("filename")
            backup_path = backup_options.get("dir_path")

        if not backup_path:
            cwd = self._get_working_path()
            backup_path = os.path.join(cwd, "backup")
        if not filename:
            tstamp = time.strftime(
                "%Y-%m-%d@%H:%M:%S", time.localtime(time.time())
            )
            filename = "%s_config.%s" % (
                task_vars["inventory_hostname"],
                tstamp,
            )

        dest = os.path.join(backup_path, filename)
        backup_path = os.path.expanduser(
            os.path.expandvars(
                to_bytes(backup_path, errors="surrogate_or_strict")
            )
        )

        if not os.path.exists(backup_path):
            os.makedirs(backup_path)

        new_task = self._task.copy()
        for item in self._task.args:
            if not item.startswith("_"):
                new_task.args.pop(item, None)

        new_task.args.update(dict(content=content, dest=dest))
        copy_action = self._shared_loader_obj.action_loader.get(
            "copy",
            task=new_task,
            connection=self._connection,
            play_context=self._play_context,
            loader=self._loader,
            templar=self._templar,
            shared_loader_obj=self._shared_loader_obj,
        )
        copy_result = copy_action.run(task_vars=task_vars)
        if copy_result.get("failed"):
            result["failed"] = copy_result["failed"]
            result["msg"] = copy_result.get("msg")
            return

        result["backup_path"] = dest
        if copy_result.get("changed", False):
            result["changed"] = copy_result["changed"]

        if backup_options and backup_options.get("filename"):
            result["date"] = time.strftime(
                "%Y-%m-%d",
                time.gmtime(os.stat(result["backup_path"]).st_ctime),
            )
            result["time"] = time.strftime(
                "%H:%M:%S",
                time.gmtime(os.stat(result["backup_path"]).st_ctime),
            )

        else:
            result["date"] = tstamp.split("@")[0]
            result["time"] = tstamp.split("@")[1]
            result["shortname"] = result["backup_path"][::-1].split(".", 1)[1][
                ::-1
            ]
            result["filename"] = result["backup_path"].split("/")[-1]

        # strip out any keys that have two leading and two trailing
        # underscore characters
        for key in list(result.keys()):
            if PRIVATE_KEYS_RE.match(key):
                del result[key]

    def _get_working_path(self):
        cwd = self._loader.get_basedir()
        if self._task._role is not None:
            cwd = self._task._role._role_path
        return cwd

    def _handle_src_option(self, convert_data=True):
        src = self._task.args.get("src")
        working_path = self._get_working_path()

        if os.path.isabs(src) or urlsplit("src").scheme:
            source = src
        else:
            source = self._loader.path_dwim_relative(
                working_path, "templates", src
            )
            if not source:
                source = self._loader.path_dwim_relative(working_path, src)

        if not os.path.exists(source):
            raise AnsibleError("path specified in src not found")

        try:
            with open(source, "r") as f:
                template_data = to_text(f.read())
        except IOError as e:
            raise AnsibleError(
                "unable to load src file {0}, I/O error({1}): {2}".format(
                    source, e.errno, e.strerror
                )
            )

        # Create a template search path in the following order:
        # [working_path, self_role_path, dependent_role_paths, dirname(source)]
        searchpath = [working_path]
        if self._task._role is not None:
            searchpath.append(self._task._role._role_path)
            if hasattr(self._task, "_block:"):
                dep_chain = self._task._block.get_dep_chain()
                if dep_chain is not None:
                    for role in dep_chain:
                        searchpath.append(role._role_path)
        searchpath.append(os.path.dirname(source))
        self._templar.environment.loader.searchpath = searchpath
        self._task.args["src"] = self._templar.template(template_data)

    def _get_network_os(self, task_vars):
        if "network_os" in self._task.args and self._task.args["network_os"]:
            display.vvvv("Getting network OS from task argument")
            network_os = self._task.args["network_os"]
        elif self._play_context.network_os:
            display.vvvv("Getting network OS from inventory")
            network_os = self._play_context.network_os
        elif (
            "network_os" in task_vars.get("ansible_facts", {})
            and task_vars["ansible_facts"]["network_os"]
        ):
            display.vvvv("Getting network OS from fact")
            network_os = task_vars["ansible_facts"]["network_os"]
        else:
            raise AnsibleError(
                "ansible_network_os must be specified on this host"
            )

        return network_os

    def _check_dexec_eligibility(self, host):
        """ Check if current python and task are eligble
        """
        dexec = self.get_connection_option("import_modules")

        # log early about dexec
        if dexec:
            display.vvvv(
                "{prefix} enabled via connection option".format(
                    prefix=DEXEC_PREFIX
                ),
                host=host,
            )
        else:
            display.vvvv("{prefix} disabled".format(prefix=DEXEC_PREFIX), host)
            display.vvvv(
                "{prefix} module execution time may be extended".format(
                    prefix=DEXEC_PREFIX
                ),
                host,
            )

        # disable dexec when running async
        if self._task.async_val and dexec:
            dexec = False
            display.vvvv(
                "{prefix} disabled for a task using async".format(
                    prefix=DEXEC_PREFIX
                ),
                host=host,
            )

        # disable dexec when not PY3
        if not PY3:
            dexec = False
            display.vvvv(
                "{prefix} disabled for when not Python 3".format(
                    prefix=DEXEC_PREFIX
                ),
                host=host,
            )
        return dexec

    def _find_load_module(self):
        """ Use the task action to find a module
        and import it.

        :return filename: The module's filename
        :rtype filename: str
        :return module: The loaded module file
        :rtype module: module
        """
        import importlib

        mloadr = self._shared_loader_obj.module_loader

        # 2.10
        try:
            context = mloadr.find_plugin_with_context(
                self._task.action, collection_list=self._task.collections
            )
            filename = context.plugin_resolved_path
            module = importlib.import_module(context.plugin_resolved_name)
        # 2.9
        except AttributeError:
            fullname, filename = mloadr.find_plugin_with_name(
                self._task.action, collection_list=self._task.collections
            )
            module = importlib.import_module(fullname)
        return filename, module

    def _patch_update_module(self, module, task_vars):
        """ Update a module instance, replacing it's AnsibleModule
        with one that doesn't load params

        :param module: An loaded module
        :type module: A module file that was loaded
        :param task_vars: The vars provided to the task
        :type task_vars: dict
        """
        import copy
        from ansible.module_utils.basic import AnsibleModule as _AnsibleModule

        # build an AnsibleModule that doesn't load params
        class PatchedAnsibleModule(_AnsibleModule):
            def _load_params(self):
                pass

        # update the task args w/ all the magic vars
        self._update_module_args(self._task.action, self._task.args, task_vars)

        # set the params of the ansible module cause we're not using stdin
        # use a copy so the module doesn't change the original task args
        PatchedAnsibleModule.params = copy.deepcopy(self._task.args)

        # give the module our revised AnsibleModule
        module.AnsibleModule = PatchedAnsibleModule

    def _exec_module(self, module):
        """ exec the module's main() since modules
        print their result, we need to replace stdout
        with a buffer. If main() fails, we assume that as stderr
        Once we collect stdout/stderr, use our super to json load
        it or handle a traceback

        :param module: An loaded module
        :type module: A module file that was loaded
        :return module_result: The result of the module
        :rtype module_result: dict
        """
        import io
        import sys
        from ansible.vars.clean import remove_internal_keys
        from ansible.module_utils._text import to_native

        # preserve previous stdout, replace with buffer
        sys_stdout = sys.stdout
        sys.stdout = io.StringIO()

        # run the module, catch the SystemExit so we continue
        try:
            module.main()
        except SystemExit:
            # module exited cleanly
            stdout = sys.stdout.getvalue()
            stderr = ""
        except Exception as exc:
            # dirty module or connection traceback
            stderr = to_native(exc)
            stdout = ""

        # restore stdout & stderr
        sys.stdout = sys_stdout

        # parse the response
        dict_out = {
            "stdout": stdout,
            "stdout_lines": stdout.splitlines(),
            "stderr": stderr,
            "stderr_lines": stderr.splitlines(),
        }
        data = self._parse_returned_data(dict_out)
        # Clean up the response like action _execute_module
        remove_internal_keys(data)

        # split stdout/stderr into lines if needed
        if "stdout" in data and "stdout_lines" not in data:
            # if the value is 'False', a default won't catch it.
            txt = data.get("stdout", None) or u""
            data["stdout_lines"] = txt.splitlines()
        if "stderr" in data and "stderr_lines" not in data:
            # if the value is 'False', a default won't catch it.
            txt = data.get("stderr", None) or u""
            data["stderr_lines"] = txt.splitlines()

        return data

    def _sanitize_contents(self, contents, filters):
        """ remove lines from contents that match
        regexes specified in the `filters` list
        """
        for x in filters:
            contents = re.sub(x, "", contents)
        return contents.strip()
