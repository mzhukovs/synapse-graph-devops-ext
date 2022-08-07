# Synapse Graph Azure DevOps Pipeline Task

## About
todo

## Dev

### Compile TypeScript files
Run ```tsc``` in PS to compile the task ts files to js

### Prepare for packaging
Note each TASK has a package.json that you need to run ```npm install``` on within the task sub-folder and it does need to be included in the vsix. See: https://github.com/microsoft/azure-pipelines-task-lib/issues/485

## Testing

### Locally

Just run ```node synapse_graph_task/synapse_graph_task.js``` in PS

But first set the inputs as env vars in the PS session, e.g.:

```$env:INPUT_WORKSPACE="synapseWorkspaceName"```

## Publishing

### Package to VSIX

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
