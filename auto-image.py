#!/usr/bin/env python
#coding: utf8

import os
import sys
import getopt
import datetime
import requests


file_tmp_dir="/tmp"
allow_jdk_version = ["1.7", "1.8"]
allow_job_prefix_list = ['dev', 'qa', 'A-daily', 'A-qa']
allow_env_list = ['daily', 'qa']
max_replicas = 10

base_build_dir="/var/jenkins/build_images"
scripts_dir = "/var/jenkins/scripts"
build_image_script = "build_image.sh"
cmdb_url = "http://*.*.*.*:0000/dict.txt"


def get_help_info():
    print('''
usage: %s --source source_path --project project_name --port service_port
    --source source_path    #the real path of the file
    --project project_name  #project name will use for image name
    --view name             #the name of jenkins view name use for specify the image tags, use with --id
    --jdk 1.7|1.8           #specify the jdk version you want to use, only support 1.7 or 1.8.
    ''' % os.path.realpath(sys.argv[0]))
    sys.exit(1)


def log(msg):
    print("%s %s" % (datetime.datetime.now(), msg))


def get_job_prefix(job_name):
    job_prefix = None
    for allow_job_prefix in allow_job_prefix_list:
        if allow_job_prefix in job_name:
            job_prefix = allow_job_prefix
            break
    if job_prefix is None:
        log("[ERROR] job %s not allow to build image, only support for job prefix in %s" % (job_name, allow_job_prefix_list))
        sys.exit(403)
    return job_prefix


def get_registry_project_name(job_prefix):
    registry_project = "public"
    if "fd-" in job_prefix:
        registry_project = "psa"
    return registry_project


def get_env_name(job_prefix):
    env_name = None
    if "daily" in job_prefix:
        env_name = "daily"
    elif "-qa" in job_prefix:
        env_name = "qa"
    if env_name is None:
        log("[ERROR] cat't get env name from job name, please make sure the allowed env name in your job name %s" % allow_env_list)
        sys.exit(403)
    return env_name


def get_deploy_info(project_name):
    deploy_type = "war"
    root_location = "default_root_location"
    port = 8080
    script = None
    dubbo_port = 0
    try:
        res = requests.get(cmdb_url)
        deploy_info_dict = res.json()
        replace_deploy_name = project_name.replace('-', '_')
        if replace_deploy_name in deploy_info_dict.keys():
            deploy_info = deploy_info_dict[replace_deploy_name]
            deploy_type = deploy_info["deploy"]
            if deploy_type != "war":
                port = deploy_info["port"]
            if deploy_type == "shell":
                script = deploy_info["script"]
            if "dubbo" in deploy_info.keys():
                dubbo_port = deploy_info["dubbo"]
            if "root" in deploy_info.keys():
                root_location = deploy_info["root"]
                if root_location == 'default':
                    root_location = project_name
    except Exception as e:
        log("[ERROR] get deploy info failed, url: %s" % cmdb_url)
        sys.exit(503)
    return deploy_type, port, script, dubbo_port, root_location


def check_file_is_exist(file_name):
    file_path = "%s/%s" % (file_tmp_dir, file_name)
    if not os.path.exists(file_path):
        log("[ERROR] file %s not found!" % file_path)
        sys.exit(404)


def get_options():
    jdk_version = "1.7"
    replicas = 1
    source_file = project_name = job_name = None
    try:
        options, args = getopt.getopt(sys.argv[1:], "h", [ "help", "source=", "project=", "port=", "name=", "jdk=", "replicas="])
        for name, value in options:
            if name in ["-h", "--help"]:
                get_help_info()
            elif name in ["--source"]:
                source_file = value
            elif name in ["--project"]:
                project_name = value
            elif name in ["--name"]:
                job_name = value
            elif name in ["--jdk"]:
                jdk_version = value
            elif name in ["--replicas"]:
                replicas = int(value)
            else:
                log("[ERROR] Invalid paraments: %s" % name)
                get_help_info()
    except Exception as e:
        log("[ERROR] Invalid paraments: %s" % e.__str__())
        sys.exit(1)
    if source_file is None:
        log("[ERROR] please give the source file path with option --source")
    elif project_name is None:
        log("[ERROR] please give the project name with option --project")
    elif job_name is None:
        log("[ERROR] please give the job name with option --name")
    elif not (0 < replicas < max_replicas):
        log("[ERROR] Invalid replicas number, the number must be large than 0 and less than %s." % max_replicas)
    else:
        if jdk_version not in allow_jdk_version:
            log("[ERROR] unknown jdk version %s, support versions are %s" %(jdk_version, allow_jdk_version))
            sys.exit(403)
        return source_file, project_name, job_name, jdk_version, replicas
    sys.exit(404)


def build_and_deploy(deploy_type, source_file, project_name, port, registry_project, jdk_version, replicas, env_name, job_prefix, dubbo_port, root_location):
    cmd = "/bin/bash %s/%s %s %s %s %s %s %s %s %s %s %s %s" % (scripts_dir, build_image_script, deploy_type, source_file, project_name, port, registry_project, jdk_version, replicas, env_name, job_prefix, dubbo_port, root_location)
    res = os.system(cmd)
    if res != 0:
        sys.exit(1)


def main():
    source_file, project_name, job_name, jdk_version, replicas = get_options()
    check_file_is_exist(source_file)
    deploy_type, port, script, dubbo_port, root_location = get_deploy_info(project_name)
    job_prefix = get_job_prefix(job_name)
    registry_project = get_registry_project_name(job_prefix)
    env_name = get_env_name(job_prefix)
    build_and_deploy(deploy_type, source_file, project_name, port, registry_project, jdk_version, replicas, env_name, job_prefix, dubbo_port, root_location)


if __name__ == '__main__':
    main()
