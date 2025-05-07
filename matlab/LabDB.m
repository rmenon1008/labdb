classdef LabDB
    % LabDB - MATLAB API for the labdb Python package
    %
    % This class provides the main entry point for the MATLAB API to the
    % labdb Python package. It handles initialization of the Python
    % environment and provides methods to create logger and query objects.
    
    properties (Access = private)
        PythonModuleInitialized = false;
    end
    
    methods
        function obj = LabDB()
            % Constructor initializes the Python environment
            obj.initializePython();
        end
        
        function logger = createLogger(obj, path, notes_mode)
            % Create an ExperimentLogger object
            %
            % Parameters:
            %   path (string): The path to log experiments to (optional)
            %   notes_mode (string): Notes mode (optional, default: 'ask-every')
            %
            % Returns:
            %   ExperimentLoggerMatlab: A new logger object
            
            if nargin < 2
                path = py.None;
            end
            
            if nargin < 3
                notes_mode = 'ask-every';
            end
            
            % Create Python ExperimentLogger
            py_logger = py.labdb.api.ExperimentLogger(path, notes_mode);
            
            % Create MATLAB wrapper
            logger = ExperimentLoggerMatlab(py_logger);
        end
        
        function query = createQuery(obj)
            % Create an ExperimentQuery object
            %
            % Returns:
            %   ExperimentQueryMatlab: A new query object
            
            % Create Python ExperimentQuery
            py_query = py.labdb.api.ExperimentQuery();
            
            % Create MATLAB wrapper
            query = ExperimentQueryMatlab(py_query);
        end
    end
    
    methods (Access = private)
        function initializePython(obj)
            % Initialize the Python environment and import required modules
            if ~obj.PythonModuleInitialized
                try
                    % Check if Python is available
                    if ~exist('py.labdb.api', 'class')
                        % Add Python module to path if needed
                        warning(['labdb Python module not found in MATLAB Python path. ', ...
                               'Make sure the labdb package is installed in your Python environment.']);
                    else
                        obj.PythonModuleInitialized = true;
                    end
                catch ME
                    error('Failed to initialize Python environment: %s', ME.message);
                end
            end
        end
    end
end 