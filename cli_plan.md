1. Setup and DB Management

```
$ labdb setup
ENTER to keep, Ctrl-C to cancel changes
MongoDB connection string [current: mongodb://localhost:27017/labdb]:
MongoDB database name [current: labdb]:
Large file storage location (none, grid-fs, local) [current: none]: 
IF USER SELECTED LOCAL: Local storage directory [current: ~/labdb-storage/]:
✅ LabDB setup successful OR ❌ LabDB setup error: ERROR
```

```
$ labdb setup show
Config file path: ~/.labdb-config.json
MongoDB connection string: mongodb://localhost:27017/labdb
MongoDB database name: labdb
Large file storage location (none, grid-fs, local): local
Local storage directory: current: ~/labdb-storage/
```

```
$ labdb setup check
✅ LabDB setup working OR ❌ LabDB setup error: ERROR
```
