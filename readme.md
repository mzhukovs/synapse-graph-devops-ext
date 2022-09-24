# Synapse Graph Azure DevOps Pipeline Task

## About
Azure DevOps task to use in your Azure DevOps pipelines to show the dependencies of those OTHER types of pipelines you have in Synapse!

e.g. output:

```mermaid
graph LR;

        classDef redBorder stroke:red,stroke-width:4px;
        classDef greenBorder stroke:#0f0,stroke-width:4px;
        classDef blueBorder stroke:#1874BA,stroke-width:4px;
        classDef blueFill stroke:#1874BA,fill:#1874BA,stroke-width:4px;
        classDef lightBlueBorder stroke:#74CAE7,stroke-width:4px;
        classDef lightBlueFill stroke:#74CAE7,fill:#74CAE7,stroke-width:4px,color:black;
        classDef orangeBorder stroke:#FF6A00,stroke-width:4px;
        classDef yellowBorder stroke:yellow,stroke-width:4px;
        classDef whiteBorder stroke:white,stroke-width:4px;
        classDef purpleBorder stroke:purple,stroke-width:4px;
        classDef grayBorder stroke:gray,stroke-width:4px;
        classDef grayFill stroke:gray,fill:gray,stroke-width:4px;
    
subgraph Legend
direction RL;
LegendTriggerStarted>"Trigger (started)"]:::greenBorder
LegendTriggerStopped>"Trigger (stopped)"]:::redBorder
LegendPipeline[["Pipeline"]]:::blueBorder
LegendLinkedService{{"LinkedService"}}:::purpleBorder
LegendDataset["Dataset"]:::lightBlueBorder
LegendIntegrationRuntime("IntegrationRuntime"):::blueFill
end
0{{"WorkspaceDefaultStorage"}}:::purpleBorder --> 7("AutoResolveIntegrationRuntime"):::blueFill
2["DS_PARQUET_WRITE"]:::lightBlueBorder --> 0{{"WorkspaceDefaultStorage"}}:::purpleBorder
3["DS_Assets"]:::lightBlueBorder --> 11[["PL_GetEquity"]]:::blueBorder
4{{"LS_Assets"}}:::purpleBorder --> 10{{"MyAzureKeyVault"}}:::purpleBorder
4{{"LS_Assets"}}:::purpleBorder --> 9("SelfHostedIntegrationRuntime"):::blueFill
4{{"LS_Assets"}}:::purpleBorder --> 3["DS_Assets"]:::lightBlueBorder
5["DS_Debts"]:::lightBlueBorder --> 11[["PL_GetEquity"]]:::blueBorder
6{{"LS_Debts"}}:::purpleBorder --> 10{{"MyAzureKeyVault"}}:::purpleBorder
6{{"LS_Debts"}}:::purpleBorder --> 9("SelfHostedIntegrationRuntime"):::blueFill
6{{"LS_Debts"}}:::purpleBorder --> 5["DS_Debts"]:::lightBlueBorder
11[["PL_GetEquity"]]:::blueBorder --> 2["DS_PARQUET_WRITE"]:::lightBlueBorder
12[["PL_GetEquity_MAIN"]]:::blueBorder --> 11[["PL_GetEquity"]]:::blueBorder
13>"DailyMidnightShedule"]:::greenBorder --> 12[["PL_GetEquity_MAIN"]]:::blueBorder
```

## Dev

### Compile TypeScript files
Run ```tsc``` in PS to compile the task ts files to js

### Prepare for packaging
Note each TASK has a package.json that you need to run ```npm install``` on within the task sub-folder and it does need to be included in the vsix. See: https://github.com/microsoft/azure-pipelines-task-lib/issues/485

## Testing

### Locally

Just run ```node synapse_graph_task/synapse_graph_task.js``` in PS

But first set the inputs as env vars in the PS session, e.g.:

```
$env:LOCAL_TEST="true"
$env:INPUT_workspace="synapseWorkspaceName"
$env:INPUT_artifactStagingDirectory="C:\Repos\synapse-graph-devops-ext"
$env:INPUT_synapseDirectory="C:\Repos\synapse-graph-devops-ext\synapse"
```

## Publishing

### Package to VSIX

Be sure to run  ```tsc``` in PS to compile the task ts files to js first then:

```
tfx extension create --manifest-globs vss-extension-manifest.json --rev-version
```

:warning: This increments the PATCH version number of your extension and saves the new version to your manifest. You must rev BOTH the task version (in task.json) AND the extension version.

### Publish to Marketplace

Either [manually upload](https://marketplace.visualstudio.com/manage/publishers/mark-zhukovsky) the VSIX generated from above, or can bundle into VSIX and publish in one go instead:

```
tfx extension publish --manifest-globs vss-extension-manifest.json --share-with zhukovsky
```

--share-with is optional, in this case my private VS "organization"

But to share publicly (instead of specific organization) must be a verified publisher.