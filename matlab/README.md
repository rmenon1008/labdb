# LabDB MATLAB API

This is a MATLAB API for the labdb Python package, allowing MATLAB users to interact with the labdb experiment tracking system.

## Requirements

- MATLAB R2016b or newer with Python support
- Python with the labdb package installed
- NumPy (for array conversion)

## Setup

1. Make sure the labdb Python package is installed and accessible from MATLAB's Python
2. Add the `matlab` directory to your MATLAB path
3. The API consists of three main classes:
   - `LabDB`: Main entry point
   - `ExperimentLoggerMatlab`: For creating experiments and logging data
   - `ExperimentQueryMatlab`: For querying and retrieving experiments

## Usage Examples

### Initialization

```matlab
% Initialize the LabDB interface
labdb = LabDB();
```

### Creating and Using a Logger

```matlab
% Create a logger
logger = labdb.createLogger();

% View the current working directory
disp(['Working directory: ' logger.Path]);

% Create a new experiment
exp_path = logger.newExperiment();
disp(['Created experiment: ' exp_path]);

% Log data (supports scalars, vectors, matrices, structs)
logger.logData('test_scalar', 42);
logger.logData('test_vector', [1, 2, 3, 4, 5]);
logger.logData('test_matrix', eye(3));
logger.logData('test_struct', struct('a', 1, 'b', 'test', 'c', true));

% Log notes
logger.logNote('test_note', 'This is a test experiment');
logger.logNote('parameters', struct('learning_rate', 0.01, 'batch_size', 32));
```

### Querying Experiments

```matlab
% Create a query object
query = labdb.createQuery();

% Get all experiments in the current directory
exps = query.getExperiments('/', 'Recursive', true, 'Limit', 10);
disp(['Found ' num2str(length(exps)) ' experiments']);

% Get experiments from specific paths
paths = {'/path/to/experiment1', '/path/to/experiment2'};
specific_exps = query.getExperimentsInList(paths);

% Get a single experiment
exp = query.getExperiment('/path/to/specific/experiment');

% Log data to an existing experiment
query.experimentLogData(exp.path, 'additional_data', rand(5,5));

% Add a note to an existing experiment
query.experimentLogNote(exp.path, 'additional_note', 'This was added later');
```

## API Reference

### LabDB

- `logger = createLogger([path], [notes_mode])`: Create an ExperimentLogger
  - `path`: Path for the logger (optional)
  - `notes_mode`: How to handle notes, one of 'ask-every', 'ask-once', 'none' (optional)
  
- `query = createQuery()`: Create an ExperimentQuery

### ExperimentLoggerMatlab

- `path = newExperiment([name])`: Create a new experiment
  - `name`: Optional name for the experiment

- `logData(key, value)`: Log data to the current experiment
  - `key`: Data key
  - `value`: Any MATLAB value (scalar, vector, matrix, struct, etc.)

- `logNote(key, value)`: Add a note to the current experiment
  - `key`: Note key
  - `value`: Note value

### ExperimentQueryMatlab

- `experiments = getExperiments(path, [Name,Value])`: Query experiments
  - `path`: Path to query
  - Name-Value pairs:
    - `'Recursive'`: Include experiments in subdirectories
    - `'Query'`: Additional MongoDB query
    - `'Projection'`: MongoDB projection
    - `'Sort'`: MongoDB sort specification
    - `'Limit'`: Maximum number of results

- `experiments = getExperimentsInList(paths, [Name,Value])`: Get experiments from a list of paths
  - `paths`: Cell array of paths
  - Name-Value pairs:
    - `'Sort'`: MongoDB sort specification
    - `'Projection'`: MongoDB projection

- `experiment = getExperiment(path)`: Get a specific experiment
  - `path`: Full path to the experiment

- `experimentLogData(path, key, value)`: Log data to a specific experiment
  - `path`: Experiment path
  - `key`: Data key
  - `value`: Data value

- `experimentLogNote(path, key, value)`: Add a note to a specific experiment
  - `path`: Experiment path
  - `key`: Note key
  - `value`: Note value

## Data Conversion

The API handles conversion between MATLAB and Python types:

- MATLAB scalars → Python scalars
- MATLAB arrays → NumPy arrays
- MATLAB structs → Python dicts
- MATLAB cell arrays → Python lists
- Python NumPy arrays → MATLAB arrays
- Python dicts → MATLAB structs
- Python lists → MATLAB cell arrays 