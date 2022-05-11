from argparse import ArgumentParser

import yaml
from commands.subcommand import get_decorator, argument
from config.DockerConfig import DockerConfig
from github.github import latest_release
from setup import Docker, Base
from utils.utils import Helpers, run_shell_command
from deepdiff import DeepDiff
from pathlib import Path

dockercli = ArgumentParser(
    description='Docker commands')
docker_parser = dockercli.add_subparsers(dest="dockercommand")


def dockercommand(dockercommand_args=[], parent=docker_parser):
    return get_decorator(dockercommand_args, parent)


@dockercommand([
    argument("-n", "--nodetype", required=True, default="fullnode", help="Type of node fullnode or archivenode",
             action="store", choices=["fullnode", "archivenode"]),
    argument("-t", "--trustednode", required=True,
             help="Trusted node on radix network. Example format: radix//brn1q0mgwag0g9f0sv9fz396mw9rgdall@10.1.2.3",
             action="store"),
    argument("-u", "--update", help="Update the node to new version of composefile", action="store_false"),
    argument("-ts", "--enabletransactions", help="Enable transaction stream api", action="store_true"),
])
def config(args):
    release = latest_release()

    if args.nodetype == "archivenode":
        Helpers.archivenode_deprecate_message()

    config = DockerConfig(release)
    config.set_node_type(args.nodetype)
    config.set_composefile_url()
    config.set_keydetails()
    config.set_core_release(release)
    config.set_data_directory()
    config.set_network_id()
    config.set_enable_transaction(args.enabletransactions)
    config.set_trusted_node(args.trustednode)
    config.set_existing_docker_compose_file()
    config_to_dump = {"core-node": dict(config.core_node_settings)}
    print(f"Yaml of config \n{yaml.dump(config_to_dump)}")
    config_file = f"{Path.home()}/config.yaml"

    def represent_none(self, _):
        return self.represent_scalar('tag:yaml.org,2002:null', '')

    yaml.add_representer(type(None), represent_none)

    with open(config_file, 'w') as f:
        yaml.dump(config_to_dump, f, default_flow_style=False, explicit_start=True, allow_unicode=True)


@dockercommand([
    argument("-f", "--configfile", required=True,
             help="Path to config file",
             action="store"),
    argument("-a", "--autoapprove", help="Set this to true to run without any prompts", action="store_true"),
])
def setup(args):
    release = latest_release()
    autoapprove = args.autoapprove

    docker_config = DockerConfig(release)
    docker_config.loadConfig(args.configfile)
    core_node_settings = docker_config.core_node_settings
    new_compose_file = Docker.setup_new_compose_file(docker_config)

    old_compose_file = Helpers.yaml_as_dict(f"{docker_config.core_node_settings.existing_docker_compose}")
    print(dict(DeepDiff(old_compose_file, new_compose_file))
          )
    to_update = ""
    if autoapprove:
        print("In Auto mode - Updating file as suggested in above changes")
    else:
        to_update = input("\nOkay to update the file [Y/n]?:")
    if Helpers.check_Yes(to_update) or autoapprove:
        Docker.save_compose_file(docker_config, new_compose_file)

    run_shell_command(f"cat {docker_config.core_node_settings.existing_docker_compose}", shell=True)
    should_start = ""
    if autoapprove:
        print("In Auto mode -  Updating the node as per above contents of docker file")
    else:
        should_start = input("\nOkay to start the node [Y/n]?:")
    if Helpers.check_Yes(should_start) or autoapprove:
        Docker.run_docker_compose_up(core_node_settings.keydetails.keystore_password,
                                     core_node_settings.existing_docker_compose,
                                     core_node_settings.trusted_node)


@dockercommand([
    argument("-f", "--configfile", required=True,
             help="Path to config file",
             action="store"),
])
def start(args):
    release = latest_release()
    docker_config = DockerConfig(release)
    docker_config.loadConfig(args.configfile)
    core_node_settings = docker_config.core_node_settings
    Docker.run_docker_compose_up(core_node_settings.keydetails.keystore_password,
                                 core_node_settings.existing_docker_compose,
                                 core_node_settings.trusted_node)


@dockercommand([
    argument("-f", "--configfile", required=True,
             help="Path to config file",
             action="store"),
    argument("-v", "--removevolumes", help="Remove the volumes ", action="store_true"),
])
def stop(args):
    if args.removevolumes:
        print(
            """ 
            Removing volumes including Nginx volume. Nginx password needs to be recreated again when you bring node up
            """)
    release = latest_release()
    docker_config = DockerConfig(release)
    docker_config.loadConfig(args.configfile)
    core_node_settings = docker_config.core_node_settings
    Docker.run_docker_compose_down(core_node_settings.existing_docker_compose, args.removevolumes)


@dockercommand([])
def configure(args):
    Base.install_dependecies()
    Base.add_user_docker_group()
