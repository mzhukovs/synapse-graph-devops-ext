# Synapse Graph Azure DevOps Pipeline Task

## About
Azure DevOps task to use in your Azure DevOps pipelines to generate a graph to show the dependencies of those OTHER types of pipelines you have in Synapse! This will help you visualize your pipelines, linked services, etc.

The graph markdown file will be published as a build artifact.

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
    mdTarget: 'GH'
```

## Filtering

You can choose to include only certain types of Synapse objects, e.g. Pipelines and Datasets and LinkedServices only, or you can create a graph just showing all the LinkedServices, the Triggers they're tied to, and the IntegrationRuntimes they depend on (without even showing any specific Pipelines, etc.).

You also have the flexibility to use regex expressions to generate the graph for specific subsets of your workspace, e.g. any that include a certain keyword or match a certain pattern, this could be useful for large workspaces, or for targeting your graph to be only scoped to a specific job or set of pipelines.

Refer to the settings in the Azure DevOps task pane for this task and the corresponding help info there for additional details.