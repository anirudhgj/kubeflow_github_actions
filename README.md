# kubeflow_github_actions


### How to Use This Github Actions 
This workflow is similar to and strongly inspired by [NikeNano/Kubefllow-github-actions](https://github.com/NikeNano/kubeflow-github-action) repo but not using standalone Kubeflow built on GKE.

NOTE :- This github actions uses AI platform Pipelines currently.


#### Setup Github Secrets

`GKE_EMAIL`  : GCP service account email \
`GKE_KEY` : GCP service account credentials in base64 encoded format \
`GKE_PROJECT` : Google Project where the Kubernetes Cluster is defined(can be located on GCP dashboard inside "Project Info" --> "Project Name" should be used) \
`KUBEFLOW_URL` : Kubeflow URL for pipeline deployment (Kubeflow deployment without IAP)


Then, type and copy the output of 
``` bash
cat path-to-gcp-service-account-key.json | base64
```



### Example Workflow :- 

```yaml

name: Compile, Deploy and Run with versioned pipeline on Kubeflow
on:
  pull_request:
    branches:
      - "master"
    types: [opened, synchronize, closed]

jobs:
  build:
    runs-on: ubuntu-latest
      env:
        GKE_PROJECT: ${{ secrets.GKE_PROJECT }}
        GIT_SHA: ${{ github.sha }}
    steps:
    - name: checkout files in repo
      uses: actions/checkout@master
      
    - uses: GoogleCloudPlatform/github-actions/setup-gcloud@master
      with:
        version: '309.0.0'
        service_account_email: ${{ secrets.GKE_EMAIL }}
        service_account_key: ${{ secrets.GKE_KEY }}
    
    - run: |
        gcloud auth configure-docker
       
    - name: <Build Image>
      env: 
        IMAGE_NAME: <example_image>
      run: |
        docker build -t gcr.io/$GKE_PROJECT/$IMAGE_NAME:${{ env.GIT_SHA }} \
          --build-arg GITHUB_SHA="${{ env.GIT_SHA }}" \
          --build-arg GITHUB_REF="$GITHUB_REF" <path_to_directory_of_dockerfile>
                                              
    - name:  <Publish Image> 
      env: 
        IMAGE_NAME: <example_image>
      run: |
        echo gcr.io/$GKE_PROJECT/$IMAGE_NAME:${{ env.GIT_SHA }}
        docker push gcr.io/$GKE_PROJECT/$IMAGE_NAME:${{ env.GIT_SHA }}
  
  
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
        CRON_EXPRESSION: "<second minute hour day month day_of_the_week> [This example runs 15 minutes per hour :- 0 15 * ? * *]"
 ```      
        
### Mandatory inputs for submitting kubeflow pipeline

| Variable | Summary |
|:---|:---|
| KUBEFLOW_URL | The URL to your kubeflow deployment |
| ENCODED_GOOGLE_APPLICATION_CREDENTIALS | Service account with access to kubeflow and rights to deploy, see here for example, the credentials needs to be bas64 encoded. |
| GOOGLE_APPLICATION_CREDENTIALS | The path to where you like to store the secrets, which needs to be decoded from GKE_KEY (**optional parameter**). |
| PIPELINE_CODE_PATH | The full path to the python file containing the pipeline. |
| PIPELINE_FUNCTION_NAME | The name of the pipeline function the `PIPELINE_CODE_PATH` file. |
| PIPELINE_PARAMETERS_PATH | The path to pipeline parameters. |
| EXPERIMENT_NAME | The name of the kubeflow experiment within which the pipeline should run. |
| RUN_PIPELINE | If you like to also run the pipeline set `True`. |
| VERSION_GITHUB_SHA | If the pipeline containers are versioned with the github hash. |
| RUN_RECURRING_PIPELINE | If you also like to run recurring pipline runs set `True` |
| CRON_EXPRESSION | If you would like to set cron for recurring runs (`RUN_RECURRING_PIPELINE` should always be "True" to use this. |

Note :- CRON expression can be generated using this link https://www.freeformatter.com/cron-expression-generator-quartz.html