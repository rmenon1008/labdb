classdef ExperimentQueryMatlab < handle
    % ExperimentQueryMatlab - MATLAB wrapper for the labdb ExperimentQuery
    %
    % This class provides MATLAB interface to the labdb ExperimentQuery Python class.
    % It allows for querying experiments and manipulating experiment data.
    
    properties (Access = private)
        PyQuery % Python ExperimentQuery object
    end
    
    methods
        function obj = ExperimentQueryMatlab(py_query)
            % Constructor stores the Python ExperimentQuery
            %
            % Parameters:
            %   py_query: Python ExperimentQuery object
            
            obj.PyQuery = py_query;
        end
        
        function experiments = getExperiments(obj, path, varargin)
            % Query experiments at the specified path
            %
            % Parameters:
            %   path (string): Path to query
            %   Name-Value pairs:
            %     'Recursive' (logical): If true, includes experiments in subdirectories
            %     'Query' (struct): Additional MongoDB query to filter results
            %     'Projection' (struct): MongoDB projection to specify which fields to return
            %     'Sort' (cell): MongoDB sort specification
            %     'Limit' (integer): Maximum number of results to return
            %
            % Returns:
            %   struct array: Array of experiment data structures
            
            % Parse inputs
            p = inputParser;
            p.addRequired('path', @(x) ischar(x) || isstring(x));
            p.addParameter('Recursive', false, @islogical);
            p.addParameter('Query', struct(), @isstruct);
            p.addParameter('Projection', py.None, @(x) isstruct(x) || isempty(x));
            p.addParameter('Sort', py.None, @(x) iscell(x) || isempty(x));
            p.addParameter('Limit', py.None, @(x) isnumeric(x) || isempty(x));
            p.parse(path, varargin{:});
            
            % Convert MATLAB parameters to Python
            py_path = string(p.Results.path);
            py_recursive = py.bool(p.Results.Recursive);
            
            % Handle optional parameters
            if ~isempty(p.Results.Query)
                py_query = obj.structToDict(p.Results.Query);
            else
                py_query = py.None;
            end
            
            if ~isequal(p.Results.Projection, py.None) && ~isempty(p.Results.Projection)
                py_projection = obj.structToDict(p.Results.Projection);
            else
                py_projection = py.None;
            end
            
            if ~isequal(p.Results.Sort, py.None) && ~isempty(p.Results.Sort)
                py_sort = obj.cellToPyList(p.Results.Sort);
            else
                py_sort = py.None;
            end
            
            if ~isequal(p.Results.Limit, py.None) && ~isempty(p.Results.Limit)
                py_limit = int32(p.Results.Limit);
            else
                py_limit = py.None;
            end
            
            % Call Python method
            py_experiments = obj.PyQuery.get_experiments(py_path, py_recursive, ...
                py_query, py_projection, py_sort, py_limit);
            
            % Convert Python results to MATLAB
            experiments = obj.pyExperimentsToStruct(py_experiments);
        end
        
        function experiments = getExperimentsInList(obj, paths, varargin)
            % Get experiments from a list of paths
            %
            % Parameters:
            %   paths (cell array of strings): List of paths to query
            %   Name-Value pairs:
            %     'Sort' (cell): MongoDB sort specification
            %     'Projection' (struct): MongoDB projection to specify which fields to return
            %
            % Returns:
            %   struct array: Array of experiment data structures
            
            % Parse inputs
            p = inputParser;
            p.addRequired('paths', @iscell);
            p.addParameter('Sort', py.None, @(x) iscell(x) || isempty(x));
            p.addParameter('Projection', py.None, @(x) isstruct(x) || isempty(x));
            p.parse(paths, varargin{:});
            
            % Convert MATLAB cell array to Python list
            py_paths = obj.cellToPyList(p.Results.paths);
            
            % Handle optional parameters
            if ~isequal(p.Results.Sort, py.None) && ~isempty(p.Results.Sort)
                py_sort = obj.cellToPyList(p.Results.Sort);
            else
                py_sort = py.None;
            end
            
            if ~isequal(p.Results.Projection, py.None) && ~isempty(p.Results.Projection)
                py_projection = obj.structToDict(p.Results.Projection);
            else
                py_projection = py.None;
            end
            
            % Call Python method
            py_experiments = obj.PyQuery.get_experiments_in_list(py_paths, py_sort, py_projection);
            
            % Convert Python results to MATLAB
            experiments = obj.pyExperimentsToStruct(py_experiments);
        end
        
        function experiment = getExperiment(obj, path)
            % Get data for a specific experiment path
            %
            % Parameters:
            %   path (string): Full path to the experiment
            %
            % Returns:
            %   struct: Experiment data structure
            
            % Convert path to Python string
            py_path = string(path);
            
            % Call Python method
            py_experiment = obj.PyQuery.get_experiment(py_path);
            
            % Convert Python result to MATLAB
            experiment = obj.pyExperimentToStruct(py_experiment);
        end
        
        function experimentLogData(obj, path, key, value)
            % Log data to a specific experiment
            %
            % Parameters:
            %   path (string): Path to the experiment
            %   key (string): The data key
            %   value: The data value
            
            % Convert MATLAB values to Python
            py_path = string(path);
            py_key = string(key);
            py_value = obj.convertToPython(value);
            
            % Call Python method
            obj.PyQuery.experiment_log_data(py_path, py_key, py_value);
        end
        
        function experimentLogNote(obj, path, key, value)
            % Log a note to a specific experiment
            %
            % Parameters:
            %   path (string): Path to the experiment
            %   key (string): The note key
            %   value: The note value
            
            % Convert MATLAB values to Python
            py_path = string(path);
            py_key = string(key);
            py_value = obj.convertToPython(value);
            
            % Call Python method
            obj.PyQuery.experiment_log_note(py_path, py_key, py_value);
        end
    end
    
    methods (Access = private)
        function py_obj = convertToPython(obj, matlab_obj)
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
                py_obj = obj.cellToPyList(matlab_obj);
            elseif isstruct(matlab_obj)
                % Convert structs to Python dicts
                py_obj = obj.structToDict(matlab_obj);
            else
                % Try to pass directly (this might fail for complex objects)
                py_obj = matlab_obj;
            end
        end
        
        function py_list = cellToPyList(obj, cell_array)
            % Convert MATLAB cell array to Python list
            
            py_list = py.list();
            for i = 1:length(cell_array)
                py_list.append(obj.convertToPython(cell_array{i}));
            end
        end
        
        function py_dict = structToDict(obj, struct_obj)
            % Convert MATLAB struct to Python dict
            
            py_dict = py.dict();
            fields = fieldnames(struct_obj);
            for i = 1:length(fields)
                field = fields{i};
                py_dict{field} = obj.convertToPython(struct_obj.(field));
            end
        end
        
        function matlab_experiments = pyExperimentsToStruct(obj, py_experiments)
            % Convert Python list of experiments to MATLAB struct array
            
            num_experiments = double(py.len(py_experiments));
            matlab_experiments = struct('id', {}, 'path', {}, 'created_at', {}, 'data', {}, 'notes', {});
            
            for i = 1:num_experiments
                py_exp = py_experiments{i-1}; % Python indexing starts at 0
                matlab_exp = obj.pyExperimentToStruct(py_exp);
                
                % Add to struct array
                if i == 1
                    matlab_experiments = matlab_exp;
                else
                    matlab_experiments(i) = matlab_exp;
                end
            end
        end
        
        function matlab_exp = pyExperimentToStruct(obj, py_exp)
            % Convert a single Python experiment to MATLAB struct
            
            % Initialize struct
            matlab_exp = struct();
            
            % Convert basic fields
            if ~isempty(py_exp._id) && ~isequal(py_exp._id, py.None)
                matlab_exp.id = char(py_exp._id);
            end
            
            matlab_exp.path = char(py_exp.path_str);
            matlab_exp.created_at = datetime(py_exp.created_at.year, ...
                                          py_exp.created_at.month, ...
                                          py_exp.created_at.day, ...
                                          py_exp.created_at.hour, ...
                                          py_exp.created_at.minute, ...
                                          py_exp.created_at.second);
            
            % Convert data fields
            if ~isempty(py_exp.data) && ~isequal(py_exp.data, py.None)
                matlab_exp.data = struct();
                keys = cell(py.list(py_exp.data.keys()));
                
                for i = 1:length(keys)
                    key = keys{i};
                    py_value = py_exp.data{key};
                    
                    % Convert Python value to MATLAB
                    if isa(py_value, 'py.numpy.ndarray')
                        % Handle NumPy arrays
                        matlab_value = double(py.array.array('d', py_value.reshape(-1, 1).tolist()));
                        % Try to reshape if we can determine the original shape
                        if isprop(py_value, 'shape')
                            try
                                shape = double(py.array.array('d', py_value.shape));
                                matlab_value = reshape(matlab_value, fliplr(shape));
                            catch
                                % Keep as is if reshape fails
                            end
                        end
                    elseif isa(py_value, 'py.list')
                        % Handle Python lists
                        try
                            matlab_value = cell(py_value);
                        catch
                            matlab_value = py_value;
                        end
                    elseif isa(py_value, 'py.dict')
                        % Handle Python dicts
                        try
                            dict_keys = cell(py.list(py_value.keys()));
                            matlab_value = struct();
                            for j = 1:length(dict_keys)
                                dict_key = dict_keys{j};
                                matlab_value.(char(dict_key)) = py_value{dict_key};
                            end
                        catch
                            matlab_value = py_value;
                        end
                    else
                        % Try direct conversion
                        try
                            matlab_value = double(py_value);
                        catch
                            try
                                matlab_value = char(py_value);
                            catch
                                matlab_value = py_value;
                            end
                        end
                    end
                    
                    matlab_exp.data.(char(key)) = matlab_value;
                end
            end
            
            % Convert notes
            if ~isempty(py_exp.notes) && ~isequal(py_exp.notes, py.None)
                matlab_exp.notes = struct();
                keys = cell(py.list(py_exp.notes.keys()));
                
                for i = 1:length(keys)
                    key = keys{i};
                    py_value = py_exp.notes{key};
                    
                    % Try simple conversion for notes
                    try
                        if isa(py_value, 'py.bool')
                            matlab_value = logical(py_value);
                        elseif isnumeric(py_value)
                            matlab_value = double(py_value);
                        else
                            matlab_value = char(py_value);
                        end
                    catch
                        matlab_value = py_value;
                    end
                    
                    matlab_exp.notes.(char(key)) = matlab_value;
                end
            end
        end
    end
end 