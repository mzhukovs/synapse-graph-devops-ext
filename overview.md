# Synapse Graph Azure DevOps Pipeline Task

## About
Azure DevOps task to use in your Azure DevOps pipelines to show the dependencies of those OTHER types of pipelines you have in Synapse! This will help you visualize your pipelines, linked services, etc.

:warning: this task requires Python 3.8

For example, in your Azure DevOps pipeline:
```yml

# this task is required for the synapse-graph-task to work!
- task: UsePythonVersion@0
  inputs:
    versionSpec: '3.8'
    addToPath: true
    architecture: 'x64'

- task: synapse-graph-task@0
  inputs:
    workspace: 'my_synapse_ws'
    synapseDirectory: '$(Build.SourcesDirectory)/synapse'
    artifactStagingDirectory: '$(Build.ArtifactStagingDirectory)/synapsegraph'
    itemTypes: 'Trigger, Pipeline, LinkedService, Dataset, Notebook, SparkJobDefinition, BigDataPool, IntegrationRuntime'
```

e.g. output:

:::mermaid
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
:::

## Filtering

You can choose to include only certain types of Synapse objects, e.g. Pipelines and Datasets and LinkedServices only, or you can create a graph just showing all the LinkedServices, the Triggers they're tied to, and the IntegrationRuntimes they depend on (without even showing any specific Pipelines, etc.).

You also have the flexibility to use regex expressions to generate the graph for specific subsets of your workspace, e.g. any that include a certain keyword or match a certain pattern, this could be useful for large workspaces, or for targeting your graph to be only scoped to a specific job or set of pipelines.

Refer to the settings in the Azure DevOps task pane for this task and the corresponding help info there for additional details.