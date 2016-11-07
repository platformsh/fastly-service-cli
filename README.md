### Modify a service

Currently these actions will activate a new version of the service, cloned from the latest one:

##### VCL
```
python services.py --name <SERVICE_NAME> --vcl <VCL_LOCATION> --key <API_KEY>
```

##### Backend
```
python services.py --name <SERVICE_NAME> --backend <BACKEND_URL> --key <API_KEY>
```

##### Domain
```
python services.py --name <SERVICE_NAME> --domain <DOMAIN_NAME> --key <API_KEY>
```

##### All three
```
python services.py --name <SERVICE_NAME> --vcl <VCL_LOCATION> --domain <DOMAIN_NAME> --vcl <VCL_LOCATION> --key <API_KEY>
```
