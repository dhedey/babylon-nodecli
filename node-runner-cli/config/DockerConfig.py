import os
import sys
from pathlib import Path

import yaml

from config.BaseConfig import BaseConfig, SetupMode
from config.CommonDockerSettings import CommonDockerSettings
from config.GatewayDockerConfig import GatewayDockerSettings
from config.KeyDetails import KeyDetails
from env_vars import MOUNT_LEDGER_VOLUME, CORE_DOCKER_REPO_OVERRIDE
from setup.Base import Base
from utils.Prompts import Prompts
from utils.utils import Helpers


class CoreDockerSettings(BaseConfig):
    nodetype: str = "fullnode"
    composefileurl: str = None
    keydetails: KeyDetails = KeyDetails({})
    core_release: str = None
    repo: str = os.getenv(CORE_DOCKER_REPO_OVERRIDE, "radixdlt/babylon-node")
    data_directory: str = f"{Helpers.get_home_dir()}/data"
    enable_transaction: str = "false"
    trusted_node: str = None
    validator_address: str = None
    java_opts: str = "--enable-preview -server -Xms8g -Xmx8g  " \
                     "-XX:MaxDirectMemorySize=2048m " \
                     "-XX:+HeapDumpOnOutOfMemoryError -XX:+UseCompressedOops " \
                     "-Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts " \
                     "-Djavax.net.ssl.trustStoreType=jks -Djava.security.egd=file:/dev/urandom " \
                     "-DLog4jContextSelector=org.apache.logging.log4j.core.async.AsyncLoggerContextSelector"

    def __init__(self, settings: dict):
        super().__init__(settings)

    def __iter__(self):
        class_variables = {key: value
                           for key, value in self.__class__.__dict__.items()
                           if not key.startswith('__') and not callable(value)}
        for attr, value in class_variables.items():
            if attr in ['keydetails']:
                yield attr, dict(self.__getattribute__(attr))
            elif self.__getattribute__(attr):
                yield attr, self.__getattribute__(attr)

    def set_node_type(self, nodetype="fullnode"):
        self.nodetype = nodetype

    def set_core_release(self, release):
        self.core_release = release
        # Using hardcoded tag value till we publish keygen image
        self.keydetails.keygen_tag = "1.3.2"

    def ask_data_directory(self):
        if "DETAILED" in SetupMode.instance().mode:
            self.data_directory = Base.get_data_dir(create_dir=False)
        if os.environ.get(MOUNT_LEDGER_VOLUME, "true").lower() == "false":
            self.data_directory = None
        if self.data_directory:
            Path(self.data_directory).mkdir(parents=True, exist_ok=True)

    def ask_enable_transaction(self):
        if "DETAILED" in SetupMode.instance().mode:
            self.enable_transaction = Prompts.ask_enable_transaction()
        elif "GATEWAY" in SetupMode.instance().mode:
            self.enable_transaction = "true"

    def set_trusted_node(self, trusted_node):
        if not trusted_node:
            trusted_node = Prompts.ask_trusted_node()
        self.trusted_node = trusted_node

    def create_config(self, release, trustednode, ks_password, new_keystore, validator):

        self.set_core_release(release)
        self.set_trusted_node(trustednode)
        self.ask_validator_address(validator)
        self.keydetails = Base.ask_keydetails(ks_password, new_keystore)
        self.ask_data_directory()
        self.ask_enable_transaction()
        return self

    def set_validator_address(self, validator_address: str):
        self.validator_address = validator_address

    def ask_validator_address(self, validator_address=None):
        if validator_address is None:
            validator_address = Prompts.ask_validator_address()
        self.set_validator_address(validator_address)


class DockerConfig(BaseConfig):
    core_node: CoreDockerSettings = CoreDockerSettings({})
    common_config: CommonDockerSettings = CommonDockerSettings({})
    gateway_settings: GatewayDockerSettings = GatewayDockerSettings({})

    def __init__(self, release: str):
        self.core_node = CoreDockerSettings({})
        self.common_config = CommonDockerSettings({})
        self.gateway_settings = GatewayDockerSettings({})
        self.core_node.core_release = release

    def loadConfig(self, file):
        my_file = Path(file)
        if not my_file.is_file():
            sys.exit("Unable to find config file"
                     "Run `radixnode docker init` to setup one")
        with open(file, 'r') as file:
            config_yaml = yaml.safe_load(file)
            core_node = config_yaml["core_node"]
            common_config = config_yaml["common_config"]
            self.core_node.core_release = core_node.get("core_release", None)
            self.core_node.data_directory = core_node.get("data_directory", None)
            self.core_node.genesis_json_location = core_node.get("genesis_json_location", None)
            self.core_node.enable_transaction = core_node.get("enable_transaction", False)
            self.common_config = CommonDockerSettings(
                {"network_id": common_config.get("network_id", "1")})
            self.core_node.keydetails = KeyDetails(core_node.get("keydetails", None))
            self.core_node.trusted_node = core_node.get("trusted_node", None)
            self.core_node.existing_docker_compose = core_node.get("docker_compose", None)

    def to_yaml(self):
        config_to_dump = dict(self)
        config_to_dump["common_config"] = dict(self.common_config)
        config_to_dump["core_node"] = dict(self.core_node)
        config_to_dump["gateway_settings"] = dict(self.gateway_settings)
        return yaml.dump(config_to_dump, sort_keys=False, default_flow_style=False, explicit_start=True,
                         allow_unicode=True)
