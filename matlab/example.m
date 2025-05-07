%% LabDB MATLAB API Example
% This script demonstrates how to use the MATLAB API for labdb.

% Initialize the LabDB interface
labdb = LabDB();

%% Example 1: Creating and using a logger
% Create a logger
logger = labdb.createLogger();
disp(['Working directory: ' logger.Path]);

% Create a new experiment
exp_path = logger.newExperiment();
disp(['Created experiment: ' exp_path]);

% Log some data
logger.logData('test_scalar', 42);
logger.logData('test_vector', [1, 2, 3, 4, 5]);
logger.logData('test_matrix', eye(3));
logger.logData('test_struct', struct('a', 1, 'b', 'test', 'c', true));

% Log some notes
logger.logNote('test_note', 'This is a test experiment');
logger.logNote('parameters', struct('learning_rate', 0.01, 'batch_size', 32));

%% Example 2: Querying experiments
% Create a query object
query = labdb.createQuery();

% Get all experiments in the current directory
exps = query.getExperiments('/', 'Recursive', true, 'Limit', 10);
disp(['Found ' num2str(length(exps)) ' experiments']);

% Display experiment details
if ~isempty(exps)
    disp('Latest experiment:');
    disp(['  Path: ' exps(1).path]);
    disp(['  Created at: ' datestr(exps(1).created_at)]);
    
    % Display notes
    if isfield(exps(1), 'notes') && ~isempty(fieldnames(exps(1).notes))
        disp('  Notes:');
        note_fields = fieldnames(exps(1).notes);
        for i = 1:length(note_fields)
            field = note_fields{i};
            value = exps(1).notes.(field);
            if isstruct(value)
                disp(['    ' field ': <struct>']);
            elseif ischar(value) || isstring(value)
                disp(['    ' field ': ' char(value)]);
            else
                disp(['    ' field ': ' num2str(value)]);
            end
        end
    end
    
    % Display data
    if isfield(exps(1), 'data') && ~isempty(fieldnames(exps(1).data))
        disp('  Data:');
        data_fields = fieldnames(exps(1).data);
        for i = 1:length(data_fields)
            field = data_fields{i};
            disp(['    ' field ': <data>']);
        end
    end
end

% Get a specific experiment
if ~isempty(exps)
    specific_exp = query.getExperiment(exps(1).path);
    disp(['Retrieved experiment: ' specific_exp.path]);
    
    % Log additional data to an existing experiment
    query.experimentLogData(specific_exp.path, 'additional_data', rand(5,5));
    disp('Logged additional data to the experiment');
end 