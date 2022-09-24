import tl = require('azure-pipelines-task-lib/task');
import { Options, PythonShell } from 'python-shell';

import os = require('os');
import path = require('path');
var process = require('process');
import * as fs from 'fs';
import * as tr from 'azure-pipelines-task-lib/toolrunner';

// used for escaping the path to the Invoke-Robocopy.ps1 script that is passed to the powershell command
let pathToScriptPSString = (filePath: string) => {
    // remove double quotes
    let result: string = filePath.replace(/"/g, '');

    // double-up single quotes and enclose in single quotes. this is to create a single-quoted string in powershell.
    result = result.replace(/'/g, "''");
    return `'${result}'`;
}

// used for escaping file paths that are ultimately passed to robocopy (via the powershell command)
let pathToRobocopyPSString = (filePath: string) => {
    // the path needs to be fixed-up due to a robocopy quirk handling trailing backslashes.
    //
    // according to http://ss64.com/nt/robocopy.html:
    //   If either the source or desination are a "quoted long foldername" do not include a
    //   trailing backslash as this will be treated as an escape character, i.e. "C:\some path\"
    //   will fail but "C:\some path\\" or "C:\some path\." or "C:\some path" will work.
    //
    // furthermore, PowerShell implicitly double-quotes arguments to external commands when the
    // argument contains unquoted spaces.
    //
    // note, details on PowerShell quoting rules for external commands can be found in the
    // source code here:
    // https://github.com/PowerShell/PowerShell/blob/v0.6.0/src/System.Management.Automation/engine/NativeCommandParameterBinder.cs

    // remove double quotes
    let result: string = filePath.replace(/"/g, '');

    // append a "." if the path ends with a backslash. e.g. "C:\some path\" -> "C:\some path\."
    if (result.endsWith('\\')) {
        result += '.';
    }

    // double-up single quotes and enclose in single quotes. this is to create a single-quoted string in powershell.
    result = result.replace(/'/g, "''");
    return `'${result}'`;
}

/**
 * Creates plain (not compressed) tar archive from files located in `filesPath`.
 * `filesPath` input may contain a file or a folder with files.
 * Puts created tar file to temp directory ($(Agent.TempDirectory)/`artifactName`.tar).
 *
 * @param filesPath path to a file or a directory of files to add to a tar archive
 * @param artifactName the name of the artifact. This will be used to determine tar archive name
 * @returns string
 */
function createTarArchive(filesPath: string, artifactName: string): string {
    const tar: tr.ToolRunner = tl.tool(tl.which('tar', true));
    const outputFilePath: string = path.join(tl.getVariable('Agent.TempDirectory') ?? "", `${artifactName}.tar`);

    if (tl.stats(filesPath).isFile()) {
        // If filesPath is a file, we only have to add a single file
        tar.arg(['cf', outputFilePath, '--directory', path.dirname(filesPath), path.basename(filesPath)]);
    } else {
        // If filesPath is a directory, we have to add all files from that directory to the tar archive
        tar.arg(['cf', outputFilePath, '--directory', filesPath, '.']);
    }

    const tarExecResult: tr.IExecSyncResult = tar.execSync();

    if (tarExecResult.error || tarExecResult.code !== 0) {
        throw new Error(`Couldn't add artifact files to a tar archive: ${tarExecResult.error}`);
    }

    return outputFilePath;
}

/**
 * If the `StoreAsTar` input is set to false, return path to publish unaltered;
 * otherwise add all files from this path to a tar archive and return path to that archive
 *
 * @param pathToPublish value of `PathtoPublish` input
 * @param shouldStoreAsTar value of `PathtoPublish` input
 * @param artifactName value of `ArtifactName` input
 * @returns string
 */
function getPathToUploadAndCreateTarIfNeeded(
    pathToPublish: string,
    shouldStoreAsTar: boolean,
    artifactName: string
): string {
    if (!shouldStoreAsTar) {
        return pathToPublish;
    }

    return createTarArchive(pathToPublish, artifactName);
}


/**
 * Publishes any saved folders/files from a given directory as artifacts. Saves user a step.
 *
 * @param pathToPublish pathToPublish is a folder or a single file that may be added to a tar archive later
 * @param artifactName the name for the published artifact
 * @param artifactType must be either "Container" for Azure Pipelines or "FilePath" for a file share
 * @param shouldStoreAsTar whether to save artifact as Tar
 * @param targetPath the file share to which the artifact files will be copied if using artifactType FilePath. This can include variables or "FilePath" for a file share.
 * @param parallel whether or not to copy in parallel if using artifactType FilePath.
 * @returns void
 */
async function publishArtifact(pathToPublish: string, artifactName: string, artifactType: string, shouldStoreAsTar: boolean = false, targetPath: string = "", parallel: boolean = false) {

    // tl.getBoolInput('StoreAsTar');
    // tl.getPathInput('PathtoPublish', true, true);
    // tl.getInput('ArtifactName', true);
    // tl.getInput('ArtifactType', true);
    // tl.getInput('TargetPath', true);
    // tl.getBoolInput('Parallel', false);

    const isWindows = os.platform() === 'win32';
    if (isWindows && shouldStoreAsTar) {
        tl.setResult(tl.TaskResult.Failed, tl.loc('TarExtractionNotSupportedInWindows'));
        return;
    }

    // pathToUpload is an actual folder or file that will get uploaded
    const pathToUpload: string = getPathToUploadAndCreateTarIfNeeded(pathToPublish, shouldStoreAsTar, artifactName);

    let hostType = tl.getVariable('system.hostType');
    if ((hostType && hostType.toUpperCase() != 'BUILD') && (artifactType.toUpperCase() !== "FILEPATH")) {
        tl.setResult(tl.TaskResult.Failed, tl.loc('ErrorHostTypeNotSupported'));
        return;
    }

    artifactType = artifactType.toLowerCase();
    let data: { [key: string]: any } = {
        artifacttype: artifactType,
        artifactname: artifactName
    };

    // upload or copy
    if (artifactType === "container") {
        data["containerfolder"] = artifactName;

        // add localpath to ##vso command's properties for back compat of old Xplat agent
        data["localpath"] = pathToUpload;
        tl.command("artifact.upload", data, pathToUpload);
    }
    else if (artifactType === "filepath") {
        if (os.platform() != 'win32') {
            // file share artifacts are not currently supported on OSX/Linux.
            tl.setResult(tl.TaskResult.Failed, tl.loc('ErrorFileShareLinux'));
            return;
        }

        let artifactPath: string = path.join(targetPath, artifactName);
        data['artifactlocation'] = targetPath; // artifactlocation for back compat with old xplat agent

        tl.mkdirP(artifactPath);

        // create the artifact. at this point, mkdirP already succeeded so the path is good.
        // the artifact should get cleaned up during retention even if the copy fails in the
        // middle
        tl.command("artifact.associate", data, targetPath);

        let parallelCount = 1;
        if (parallel) {
            parallelCount = getParallelCount();
        }

        // copy the files
        let script: string = path.join(__dirname, 'Invoke-Robocopy.ps1');
        let command: string = `& ${pathToScriptPSString(script)} -Source ${pathToRobocopyPSString(pathToUpload)} -Target ${pathToRobocopyPSString(artifactPath)} -ParallelCount ${parallelCount}`
        if (tl.stats(pathToUpload).isFile()) {
            let parentFolder = path.dirname(pathToUpload);
            let file = path.basename(pathToUpload);
            command = `& ${pathToScriptPSString(script)} -Source ${pathToRobocopyPSString(parentFolder)} -Target ${pathToRobocopyPSString(artifactPath)} -ParallelCount ${parallelCount} -File '${file}'`
        }

        let powershell = new tr.ToolRunner('powershell.exe');
        powershell.arg('-NoLogo');
        powershell.arg('-Sta');
        powershell.arg('-NoProfile');
        powershell.arg('-NonInteractive');
        powershell.arg('-ExecutionPolicy');
        powershell.arg('Unrestricted');
        powershell.arg('-Command');
        powershell.arg(command);
        powershell.on('stdout', (buffer: Buffer) => {
            process.stdout.write(buffer);
        });
        powershell.on('stderr', (buffer: Buffer) => {
            process.stderr.write(buffer);
        });
        let execOptions = { silent: true } as tr.IExecOptions;
        await powershell.exec(execOptions);
    }
}

async function run() {
    try {
        const isRunningLocally = Boolean(process.env.LOCAL_TEST);

        // console.log(process.cwd());
        tl.setResourcePath(path.join(__dirname, 'task.json'));

        const workspace: string | undefined = tl.getInput('workspace', true);
        const artifactStagingDirectory: string | undefined = tl.getPathInput('artifactStagingDirectory', true, false); // not checking if exists as we will create it if not
        const synapseDirectory: string | undefined = tl.getPathInput('synapseDirectory', true, true);
        const itemTypes: string[] | undefined = tl.getDelimitedInput('itemTypes', ",", true);
        const includePipelineRegex: string[] | undefined = tl.getDelimitedInput('includePipelineRegex', "\n", true);
        const requirePathToPipelineRegex: string[] | undefined = tl.getDelimitedInput('requirePathToPipelineRegex', "\n", true);
        const excludeRegex: string[] | undefined = tl.getDelimitedInput('excludeRegex', "\n", true);

        //#region Generate Synapse Graph outputs in staging directory via python

        const inputs = {
            "workspace": workspace,
            "synapse_directory": synapseDirectory,
            "artifact_staging_directory": artifactStagingDirectory,
            "item_types": itemTypes,
            "include_pipeline_regex": includePipelineRegex,
            "require_path_to_pipeline_regex": requirePathToPipelineRegex,
            "exclude_regex": excludeRegex
        };

        let options: Options = {
            mode: 'text', // could also be 'json' or 'binary'
            //pythonPath: 'path/to/python',
            scriptPath: __dirname, // current node dir is where both locally and on build agent this task's assets are as well (namely, our python script)
            pythonOptions: ['-u'], // get print results in real-time
            args: [JSON.stringify(inputs)] // argument which can be accessed in the script using sys.argv[1], sys.argv[2], etc.
        };

        PythonShell.run('synapse_graph_task.py', options, async function (err, result) {
            if (err) throw err;

            // result is an array consisting of print messages collected from the python script
            console.log(result?.join("\n") ?? "No python output printed.");

            if (!isRunningLocally)
                await publishArtifact(artifactStagingDirectory ?? "", "synapsegraph", "Container", false);
        });
        //#endregion
    }
    catch (err) {
        tl.setResult(tl.TaskResult.Failed, err.message);
    }
}

function getParallelCount(): number {
    let result = 8;
    let inputValue: string = "8"; // tl.getInput('ParallelCount', false);
    if (Number.isNaN(Number(inputValue))) {
        tl.warning(tl.loc('UnexpectedParallelCount', inputValue));
    }
    else {
        let parsedInput = parseInt(inputValue);
        if (parsedInput < 1) {
            tl.warning(tl.loc('UnexpectedParallelCount', parsedInput));
            result = 1;
        }
        else if (parsedInput > 128) {
            tl.warning(tl.loc('UnexpectedParallelCount', parsedInput));
            result = 128;
        }
        else {
            result = parsedInput;
        }
    }

    return result;
}

run();