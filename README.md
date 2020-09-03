# kubeflow_github_actions


### HOW TO USE THIS GITHUB ACTIONS (Similar to NikeNano/Kubefllow-github-actions repo but not using Standalone Kubeflow)

NOTE :- This github Actions uses AI platform Pipelines currently

Setup Github Secrets for the following :-

GKE_EMAIL  - GCP service account email \
GKE_KEY - GCP service account credentials in base64 encoded format 
example:- copy the output of 
``` bash
cat path-to-key.json | base64
```
\
GKE_PROJECT - Google Project where the Kubernetes Cluster is defined(can be located on GCP dashboard inside "Project Info" --> "Project Name" should be used) \
KUBEFLOW_URL - Kubeflow URL for pipeline deployment (Kubeflow deployment without IAP) \

### Example Workflow :- 

```yaml

name: Compile, Deploy and Run versioned DIEN pipeline on Kubeflow 
on: [push]

env:
  GKE_PROJECT: ${{ secrets.GKE_PROJECT }}

jobs:
  build:
  
    runs-on: ubuntu-latest
    steps:
    
    - name: checkout files in repo
      uses: actions/checkout@master
      
    - uses: GoogleCloudPlatform/github-actions/setup-gcloud@master
      with:
        version: '270.0.0'
        service_account_email: ${{ secrets.GKE_EMAIL }}
        service_account_key: ${{ secrets.GKE_KEY }}
    
    - run: |
        gcloud auth configure-docker
       
    - name: <Build Image>
      env: 
        IMAGE_NAME: <example_image>
      run: |
        docker build -t gcr.io/$GKE_PROJECT/$IMAGE_NAME:$GITHUB_SHA \
          --build-arg GITHUB_SHA="$GITHUB_SHA" \
          --build-arg GITHUB_REF="$GITHUB_REF" <path_to_directory_of_dockerfile>
                                              
    - name:  <Publish Image> 
      env: 
        IMAGE_NAME: <example_image>
      run: |
        echo gcr.io/$GKE_PROJECT/$IMAGE_NAME:$GITHUB_SHA
        docker push gcr.io/$GKE_PROJECT/$IMAGE_NAME:$GITHUB_SHA
  
  
    - name: Submit Kubeflow pipeline
      id: kubeflow
      uses: anirudhgj/kubeflow_github_actions@master
      with:
        KUBEFLOW_URL: ${{ secrets.KUBEFLOW_URL }}
        ENCODED_GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GKE_KEY }}
        GOOGLE_APPLICATION_CREDENTIALS: /tmp/gcloud-sa.json
        PIPELINE_CODE_PATH: "<path_to_pipeline_python_file>"
        PIPELINE_FUNCTION_NAME: "<name_of_the_pipeline_function_defined_in_the_pipeline_python_file>"
        PIPELINE_PARAMETERS_PATH: "<pipeline_parameters_path>"
        EXPERIMENT_NAME: "Default"
        RUN_PIPELINE: True
        VERSION_GITHUB_SHA: True
        RUN_RECURRING_PIPELINE: True
        CRON_EXPRESSION: "<second minute hour day month day_of_the_week[example :-0 0 1 ? * SUN]>"
 ```      
        
### Mandatory inputs for submitting kubeflow pipeline


KUBEFLOW_URL: The URL to your kubeflow deployment \
ENCODED_GOOGLE_APPLICATION_CREDENTIALS: Service account with access to kubeflow and rights to deploy, see here for example, the credentials needs to be bas64 encoded \
GOOGLE_APPLICATION_CREDENTIALS: The path to where you like to store the secrets, which needs to be decoded from GKE_KEY (optional parameter)\
PIPELINE_CODE_PATH: The full path to the python file containing the pipeline \
PIPELINE_FUNCTION_NAME: The name of the pipeline function the PIPELINE_CODE_PATH file \
PIPELINE_PARAMETERS_PATH: The pipeline parameters \
EXPERIMENT_NAME: The name of the kubeflow experiment within which the pipeline should run \
RUN_PIPELINE: If you like to also run the pipeline set "True" \
VERSION_GITHUB_SHA: If the pipeline containers are versioned with the github hash \
RUN_RECURRING_PIPELINE: If you also like to run recurring pipline runs set "True" \
CRON_EXPRESSION: if you would like to set cron for recurring runs (RUN_RECURRING_PIPELINE should always be "True" to use this . CRON expression can be generated using this link https://www.freeformatter.com/cron-expression-generator-quartz.html --> use "Seconds	Minutes	Hours	Day Of Month	Month	Day Of Week" part of the CRON string only


    
