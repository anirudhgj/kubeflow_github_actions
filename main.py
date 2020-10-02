import os
import sys
import json
import yaml
import logging
import kfp
import kfp.compiler as compiler
import importlib.util
from datetime import datetime
from typing import Optional


logging.basicConfig(stream=sys.stdout, level=logging.INFO)

# TODO: Remove after version up to v1.1
_FILTER_OPERATIONS = {"UNKNOWN": 0,
                      "EQUALS": 1,
                      "NOT_EQUALS": 2,
                      "GREATER_THAN": 3,
                      "GREATER_THAN_EQUALS": 5,
                      "LESS_THAN": 6,
                      "LESS_THAN_EQUALS": 7}


# TODO: Remove after version up to v1.1
def get_pipeline_id(self, name):
    """Find the id of a pipeline by name.

    Args:
        name: Pipeline name.

    Returns:
        Returns the pipeline id if a pipeline with the name exists.
    """
    pipeline_filter = json.dumps({
        "predicates": [
            {
                "op": _FILTER_OPERATIONS["EQUALS"],
                "key": "name",
                "stringValue": name,
            }
        ]
    })
    result = self._pipelines_api.list_pipelines(filter=pipeline_filter)
    if result.pipelines is None:
        return None
    if len(result.pipelines) == 1:
        return result.pipelines[0].id
    elif len(result.pipelines) > 1:
        raise ValueError(
            "Multiple pipelines with the name: {} found, the name needs to be unique".format(name))
    return None


# TODO: Remove after version up to v1.1
def upload_pipeline_version(
        self,
        pipeline_package_path,
        pipeline_version_name: str,
        pipeline_id: Optional[str] = None,
        pipeline_name: Optional[str] = None):
    """Uploads a new version of the pipeline to the Kubeflow Pipelines cluster.
    Args:
        pipeline_package_path: Local path to the pipeline package.
        pipeline_version_name:  Name of the pipeline version to be shown in the UI.
        pipeline_id: Optional. Id of the pipeline.
        pipeline_name: Optional. Name of the pipeline.
    Returns:
        Server response object containing pipleine id and other information.
    Throws:
        ValueError when none or both of pipeline_id or pipeline_name are specified
        Exception if pipeline id is not found.
    """

    if all([pipeline_id, pipeline_name]) or not any([pipeline_id, pipeline_name]):
        raise ValueError('Either pipeline_id or pipeline_name is required')

    if pipeline_name:
        pipeline_id = self.get_pipeline_id(pipeline_name)

    response = self._upload_api.upload_pipeline_version(
        pipeline_package_path,
        name=pipeline_version_name,
        pipelineid=pipeline_id
    )

    if self._is_ipython():
        import IPython
        html = 'Pipeline link <a href=%s/#/pipelines/details/%s>here</a>' % (
            self._get_url_prefix(), response.id)
        IPython.display.display(IPython.display.HTML(html))
    return response


def load_function(pipeline_function_name: str, full_path_to_pipeline: str) -> object:
    """Function to load python function from filepath and filename

    Arguments:
        pipeline_function_name {str} -- The name of the pipeline function
        full_path_to_pipeline {str} -- The full path name including the filename of the python file that 
                                        describes the pipeline you want to run on Kubeflow

    Returns:
        object -- [description]
    """
    logging.info(
        f"Loading the pipeline function from: {full_path_to_pipeline}")
    logging.info(
        f"The name of the pipeline function is: {pipeline_function_name}")
    spec = importlib.util.spec_from_file_location(pipeline_function_name,
                                                  full_path_to_pipeline)
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)
    pipeline_func = getattr(foo, pipeline_function_name)
    logging.info("Succesfully loaded the pipeline function.")
    return pipeline_func


def pipeline_compile(pipeline_function: object) -> str:
    """Function to compile pipeline. The pipeline is compiled to a zip file. 

    Arguments:
        pipeline_func {object} -- The kubeflow pipeline function

    Returns:
        str -- The name of the compiled kubeflow pipeline
    """
    pipeline_name_zip = pipeline_function.__name__ + ".zip"
    compiler.Compiler().compile(pipeline_function, pipeline_name_zip)
    logging.info("The pipeline function is compiled.")
    return pipeline_name_zip


def upload_pipeline(pipeline_name_zip: str, pipeline_name: str, github_sha: str, client):
    """ Function to upload pipeline to kubeflow.

    Arguments:
        pipeline_name_zip {str} -- The name of the compiled pipeline.ArithmeticError
        pipeline_name {str} -- The name of the pipeline function. This will be the name in the kubeflow UI. 
    """
    pipeline_id = client.get_pipeline_id(pipeline_name)
    if pipeline_id is None:
        pipeline_id = client.upload_pipeline(
            pipeline_package_path=pipeline_name_zip,
            pipeline_name=pipeline_name).to_dict()["id"]

    client.upload_pipeline_version(
        pipeline_package_path=pipeline_name_zip,
        pipeline_version_name=github_sha,
        pipeline_id=pipeline_id)

    return pipeline_id


def read_pipeline_params(pipeline_paramters_path: str) -> dict:
    # [TODO] add docstring here
    pipeline_params = {}
    with open(pipeline_paramters_path) as f:
        try:
            pipeline_params = yaml.safe_load(f)
            logging.info(f"The pipeline paramters is: {pipeline_params}")
        except yaml.YAMLError as exc:
            logging.info("The yaml parameters could not be loaded correctly.")
            raise ValueError(
                f"The yaml parameters could not be loaded correctly with {exc}.")
        logging.info(f"The paramters are: {pipeline_params}")
    return pipeline_params


def run_pipeline_func(client: kfp.Client,
                      pipeline_name: str,
                      pipeline_id: str,
                      pipeline_paramters_path: dict,
                      recurring_flag: bool = False,
                      cron_exp: str = ''):
    pipeline_params = read_pipeline_params(
        pipeline_paramters_path=pipeline_paramters_path)
    pipeline_params = pipeline_params if pipeline_params is not None else {}

    experiment_id = None
    try:
        experiment_id = client.get_experiment(
            experiment_name=os.environ["INPUT_EXPERIMENT_NAME"]
        ).to_dict()["id"]
    except ValueError:
        client.create_experiment(os.environ["INPUT_EXPERIMENT_NAME"])
        experiment_id = client.get_experiment(
            experiment_name=os.environ["INPUT_EXPERIMENT_NAME"]
        ).to_dict()["id"]

    namespace = os.getenv("INPUT_PIPELINE_NAMESPACE") if not str.isspace(
        os.getenv("INPUT_PIPELINE_NAMESPACE")) else None

    job_name = 'Run {} on {}'.format(pipeline_name,
                                     datetime.now().strftime("%Y_%m_%d_%H_%M_%S"))

    logging.info(f"experiment_id: {experiment_id}, \
                 job_name: {job_name}, \
                 pipeline_params: {pipeline_params}, \
                 pipeline_id: {pipeline_id}, \
                 namespace: {namespace}, \
                 cron_exp: {cron_exp}")

    if recurring_flag == "true":
        client.create_recurring_run(experiment_id=experiment_id,
                                    job_name=job_name,
                                    params=pipeline_params,
                                    pipeline_id=pipeline_id,
                                    cron_expression=cron_exp)
        logging.info(
            "Successfully started the recurring pipeline, head over to kubeflow to check it out")

    client.run_pipeline(experiment_id=experiment_id,
                        job_name=job_name,
                        params=pipeline_params,
                        pipeline_id=pipeline_id)
    logging.info(
        "Successfully started the pipeline, head over to kubeflow to check it out")


def main():

    logging.info(
        "Started the process to compile and upload the pipeline to kubeflow.")
    logging.info("Authenticating")

    ga_credentials = os.environ["INPUT_GOOGLE_APPLICATION_CREDENTIALS"]
    with open(ga_credentials) as f:
        sa_details = json.load(f)
    os.system("gcloud auth activate-service-account {} --key-file={} --project={}".format(sa_details['client_email'],
                                                                                          ga_credentials,
                                                                                          sa_details['project_id']))

    pipeline_name = os.environ['INPUT_PIPELINE_FUNCTION_NAME']
    pipeline_function = load_function(pipeline_function_name=pipeline_name,
                                      full_path_to_pipeline=os.environ['INPUT_PIPELINE_CODE_PATH'])

    github_sha = os.getenv("GITHUB_SHA")
    if os.environ["INPUT_VERSION_GITHUB_SHA"] == "true":
        logging.info(f"Versioned pipeline components with : {github_sha}")
        pipeline_function = pipeline_function(github_sha=github_sha)

    # TODO: Remove after version up to v1.1
    kfp.Client.get_pipeline_id = get_pipeline_id
    kfp.Client.upload_pipeline_version = upload_pipeline_version

    client = kfp.Client(host=os.environ['INPUT_KUBEFLOW_URL'])
    pipeline_name_zip = pipeline_compile(pipeline_function=pipeline_function)
    pipeline_id = upload_pipeline(pipeline_name_zip=pipeline_name_zip,
                                  pipeline_name=pipeline_name,
                                  github_sha=github_sha,
                                  client=client)

    if os.getenv("INPUT_RUN_PIPELINE") == "true":
        logging.info("Started the process to run the pipeline on kubeflow.")
        run_pipeline_func(pipeline_name=pipeline_name,
                          pipeline_id=pipeline_id,
                          client=client,
                          pipeline_paramters_path=os.environ["INPUT_PIPELINE_PARAMETERS_PATH"],
                          recurring_flag=os.environ['INPUT_RUN_RECURRING_PIPELINE'],
                          cron_exp=os.environ['INPUT_CRON_EXPRESSION'])


if __name__ == "__main__":
    main()
