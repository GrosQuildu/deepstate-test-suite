"""
client.py

    DESCRIPTION:
        API interface for interacting with test workspaces and Docker for containerized fuzzing.
        Our client object interacts with our testbed environment, manages testing workspaces,
        and spins off container fuzzing workers when necessary.

    USAGE:
        client = Client()
        client.functionality()

"""
import logging
logging.basicConfig()

import os
import shutil
import subprocess
import requests
import configparser

from fuzzbed_cli import templates
from deepstate.core.base import AnalysisBackend, ConfigType

from typing import Optional, List, Dict, Union

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(os.environ.get("FUZZBED_LOG", "INFO").upper())


class ClientError(Exception):
    pass


class Client(object):
    """
    A Client is an object that encapsulates an interface for interacting with the testing environment,
    """

    def __init__(self, test_env: str = "TESTBED") -> None:
        """
        Initializes a client to interface testing. Uses a default envvar to specify
        the path to the "testbed" of testing harnesses and artifacts.

        :param test_env: envvar to path of test harnesses and artifacts
        """

        env: str = os.environ.get(test_env)
        if env is None:
            raise ClientError("no tests found in testbed envvar `${}`.".format(test_env))
        if ':' in env:
            raise ClientError("should not have multiple paths set with testbed envvar `${}`.".format(env))

        # testbed directory root
        self.env: str = env
        LOGGER.debug("Path to testbed env: {}".format(self.env))

        # get all test workspaces from testbed directory
        self.test_paths: List[str] = [testdir[0] for testdir in os.walk(env)]


    @staticmethod
    def _init_config(conf_path: str) -> Optional[Dict[str, str]]:
        """
        Helper method that takes an input path and generates a serializable configuration from a default dict.

        :param conf_path: absolute path to directory to initialize with default config name
        """

        parser = configparser.ConfigParser()
        parser.update(templates.DEFAULT_CONFIG)

        with open(os.path.join(conf_path, templates.DEFAULT_CONFIG_NAME), "w") as conf_file:
            parser.write(conf_file)

        return vars(parser)



    def init_ws(self, _ws_name: str, config_path: Optional[str] = None, harness_paths: List[str] = []) -> str:
        """
        Creates a new workspace in the testbed environment path. If no configuration and harness(es) is provided,
        the client will initialize default ones for the user. Returns the abspath to the new testbed if successfully
        initialized.

        :param ws_name: name of workspace directory.
        :param config_path: optional path to configuration file to consume be consumed by DeepState executor.
        :param harness_paths: optional paths to existing DeepState test harnesses
        """

        # check if abspath to workspace already exists
        ws_name: str = os.path.join(self.env, _ws_name)
        if ws_name in self.test_paths:
            raise ClientError("workspace directory already exists in testbed path.")
        LOGGER.debug("Workspace path to initialize: {}".format(ws_name))

        # initialize workspace directory with ws_name
        LOGGER.info("Creating workspace directory in testbed.")
        os.mkdir(ws_name)

        # initialize new config to workspace or copy over config_path
        if config_path is None:
            LOGGER.info("Initializing a new default configuration.")
            config = Client._init_config(ws_name)
        else:
            LOGGER.info("Copying configuration `{}` to `{}`.".format(config_path, ws_name))
            shutil.copy(config_path, ws_name)

        # initialize Dockerfile
        with open(os.path.join(ws_name, "Dockerfile"), "w") as f:
            f.write(templates.DOCKERFILE)

        # if no existing harnesses are specified, write a single default one
        if len(harness_paths) == 0:
            LOGGER.info("Writing new default test harness.")
            with open(os.path.join(ws_name, templates.DEFAULT_HARNESS_NAME), "w") as f:
                f.write(templates.DEFAULT_TEST_HARNESS.replace("{HARNESS_NAME}", templates.DEFAULT_HARNESS_NAME))

        # if not, copy harnesses over to workspace
        else:
            LOGGER.info("Initializing workspace with specified harness paths.")
            for _path in harness_paths:
                path = os.path.abspath(_path)

                LOGGER.debug("Copying source harness `{}` to `{}`.".format(_path, ws_name))
                shutil.copy(path, ws_name)

        return ws_name


    @property
    def workspaces(self):
        print(self.test_paths)
