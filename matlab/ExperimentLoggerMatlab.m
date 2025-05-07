classdef ExperimentLoggerMatlab < handle
    % ExperimentLoggerMatlab - MATLAB wrapper for the labdb ExperimentLogger
    %
    % This class provides MATLAB interface to the labdb ExperimentLogger Python class.
    % It allows for creating experiments and logging data and notes.
    
    properties (Access = private)
        PyLogger % Python ExperimentLogger object
    end
    
    properties (Dependent)
        % Path where experiments are being created
        Path
        % Path of the current experiment
        CurrentExperimentPath
        % Notes mode for the logger
        NotesMode
    end
    
    methods
        function obj = ExperimentLoggerMatlab(py_logger)
            % Constructor stores the Python ExperimentLogger
            %
            % Parameters:
            %   py_logger: Python ExperimentLogger object
            
            obj.PyLogger = py_logger;
        end
        
        function path = get.Path(obj)
            % Get the current working path
            path = char(obj.PyLogger.path);
        end
        
        function exp_path = get.CurrentExperimentPath(obj)
            % Get the current experiment path
            if isempty(obj.PyLogger.current_experiment_path) || ...
                    isequal(obj.PyLogger.current_experiment_path, py.None)
                exp_path = '';
            else
                exp_path = char(obj.PyLogger.current_experiment_path);
            end
        end
        
        function notes_mode = get.NotesMode(obj)
            % Get the notes mode
            notes_mode = char(obj.PyLogger.notes_mode);
        end
        
        function experiment_path = newExperiment(obj, name)
            % Create a new experiment
            %
            % Parameters:
            %   name (string, optional): Name for the experiment
            %
            % Returns:
            %   string: Path of the created experiment
            
            if nargin < 2
                name = py.None;
            end
            
            % Call Python method
            py_path = obj.PyLogger.new_experiment(name);
            
            % Convert Python string to MATLAB string
            experiment_path = char(py_path);
        end
        
        function logData(obj, key, value)
            % Log data to the current experiment
            %
            % Parameters:
            %   key (string): The key to store the data under
            %   value: The value to store (will be converted to Python)
            
            if isempty(obj.CurrentExperimentPath)
                error('No experiment started. Use newExperiment() first.');
            end
            
            % Convert MATLAB value to Python
            py_value = obj.convertToPython(value);
            
            % Call Python method
            obj.PyLogger.log_data(key, py_value);
        end
        
        function logNote(obj, key, value)
            % Add a note to the current experiment
            %
            % Parameters:
            %   key (string): The key to store the note under
            %   value: The value to store (must be JSON serializable)
            
            if isempty(obj.CurrentExperimentPath)
                error('No experiment started. Use newExperiment() first.');
            end
            
            % Convert MATLAB value to Python
            py_value = obj.convertToPython(value);
            
            % Call Python method
            obj.PyLogger.log_note(key, py_value);
        end
    end
    
    methods (Access = private)
        function py_obj = convertToPython(~, matlab_obj)
            % Convert MATLAB objects to Python
            
            if isnumeric(matlab_obj)
                % Convert numeric arrays
                if isscalar(matlab_obj)
                    py_obj = double(matlab_obj);
                else
                    py_obj = py.numpy.array(matlab_obj);
                end
            elseif islogical(matlab_obj)
                % Convert logical values
                py_obj = py.bool(matlab_obj);
            elseif ischar(matlab_obj) || isstring(matlab_obj)
                % Convert strings
                py_obj = string(matlab_obj);
            elseif iscell(matlab_obj)
                % Convert cell arrays to Python lists
                py_list = py.list();
                for i = 1:length(matlab_obj)
                    py_list.append(obj.convertToPython(matlab_obj{i}));
                end
                py_obj = py_list;
            elseif isstruct(matlab_obj)
                % Convert structs to Python dicts
                py_obj = py.dict();
                fields = fieldnames(matlab_obj);
                for i = 1:length(fields)
                    field = fields{i};
                    py_obj{field} = obj.convertToPython(matlab_obj.(field));
                end
            else
                % Try to pass directly (this might fail for complex objects)
                py_obj = matlab_obj;
            end
        end
    end
end 