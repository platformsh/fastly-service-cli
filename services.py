import json
import subprocess
import requests
import argparse
import os

# this is required but you can also pass it in as an argument
API_KEY = os.environ.get('FASTLY_API_KEY', '')

# This can be passed into the function directly or set here
VCL_LOC = ''

class NotFoundException(Exception):
        pass


class UsageException(Exception):
        pass


class AuthException(Exception):
        pass


class FastlyException(Exception):
        pass


def make_service(name, api_key=API_KEY):
    '''
    Make a fastly service with the given name. Should take
    other params (domain name, url)
    '''
    serv = requests.post('https://api.fastly.com/service',
                         headers={"Fastly-Key": api_key,
                                  "Content-Type": "application/json",
                                  "Accept": "application/json"
                                  },
                         data=json.dumps({'name': name}))
    if serv.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(serv.text))
    return serv


def delete_service(name, api_key=API_KEY):
    '''
    Delete the service with the given name.
    '''
    sid = get_service(name, api_key)["id"]
    return requests.delete('https://api.fastly.com/service/{}'.format(sid),
                           headers={"Fastly-Key": api_key,
                                    "Accept": "application/json"
                                    })


def get_service(name, api_key=API_KEY):
    '''
    Return a service with the given name. Used for retrieving service ID.
    '''
    # get all the services
    services =  requests.get('https://api.fastly.com/service',
                             headers={"Fastly-Key": api_key,
                                      "Accept": "application/json"
                                      })
    # Get the latest version
    if services.status_code != 200:
        raise UsageException("Received error from Fastly: {}".format(services.text))
    try:
        return max([service for service in services.json()\
                    if service["name"] == name], key=lambda x: x["version"])
    except ValueError:
        raise NotFoundException("Fastly service with name {} was not found.".format(name))



def upload_vcl(name, vcl=VCL_LOC, service_version=None, api_key=API_KEY):
    '''
    Upload a VCL to the service identified by `name`.
    '''
    service = get_service(name, api_key)
    if not service_version:
        service_version = service["version"]
    resp =  upload_vcl_by_id(service["id"], service_version, vcl, api_key)
    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))
    else:
        return resp

def delete_vcl(service_name, vcl_name="main", service_version=None, api_key=API_KEY):
    '''
    Upload a VCL to the service identified by `name`.
    '''
    service = get_service(service_name, api_key)
    if not service_version:
        service_version = service["version"]
    resp = requests.delete('https://api.fastly.com/service/{0}/version/{1}/vcl/{2}'.format(service["id"], service_version, vcl_name),
                          headers={"Fastly-Key": api_key,
                                   "Accept": "application/json"
                                  })
    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))
    else:
        return resp



def upload_vcl_by_id(fastly_service_id, fastly_service_version, vcl, api_key=API_KEY):
    '''
    Upload a VCL ot the service identified by `fastly_id`.
    '''
    resp = requests.post('https://api.fastly.com/service/{0}/version/{1}/vcl'.format(fastly_service_id, fastly_service_version ),
                          headers={"Fastly-Key": api_key,
                                   "Content-Type": "application/json",
                                   "Accept": "application/json"
                                  },
                          data=json.dumps({"content": file(vcl).read(),
                                           "name": "Main"}))
    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))

    resp = requests.put('https://api.fastly.com/service/{0}/version/{1}/vcl/Main/main'.format(fastly_service_id, fastly_service_version ),
                          headers={"Fastly-Key": api_key,
                                   "Content-Type": "application/json",
                                   "Accept": "application/json"
                                  })
    return resp


def add_domain(name, domain, service_version=None, api_key=API_KEY):
    '''
    Takes (name, domain). Adds a domain to the latest version of the service.
    '''
    service_id = get_service(name, api_key)["id"]
    if not service_version:
        service_version = get_service(name)["version"]
    resp = requests.post('https://api.fastly.com/service/{}/version/{}/domain'.format(service_id,
                                                                               service_version),
                        headers={"Fastly-Key": api_key,
                                 "Content-Type": "application/json",
                                 "Accept": "application/json"
                                },
                        data=json.dumps({"name": domain}))
    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))
    else:
        return resp



def delete_domain(name, domain, api_key=API_KEY):
    '''
    Takes (name, domain). Deletes a domain from the latest version of the service.
    '''
    service_id = get_service(name)["id"]
    service_version = get_service(name)["version"]
    requests.delete('https://api.fastly.com/service/{}/version/{}/domain/{}'.format(service_id,
                                                                                    service_version,
                                                                                    domain),
                    headers={"Fastly-Key": api_key,
                             "Accept": "application/json"
                            })


def create_backend(name, backend, cert=None, cert_domain=None, service_version=None, api_key=API_KEY):
    '''
    Takes (name, backend) and updates service with `name` to use `backend`.
    '''
    service_id = get_service(name, api_key)["id"]
    if not service_version:
        service_version = get_service(name, api_key)["version"]


    backend_settings = {"address": backend,
                         "first_byte_timeout": 30000,
                         "name": "Main"}
    if cert is not None:
        with open(cert, 'r') as certfile:
            cert_body = certfile.read()

        backend_settings["port"] = 443
        backend_settings["ssl_cert_hostname"] = cert_domain
        backend_settings["ssl_check_cert"] = True
        backend_settings["ssl_ca_cert"] = cert_body
        backend_settings["use_ssl"] = True

    resp = requests.post('https://api.fastly.com/service/{}/version/{}/backend'.format(service_id,
                                                                                service_version),
                        headers={"Fastly-Key": api_key,
                                 "Content-Type": "application/json",
                                 "Accept": "application/json",
                                },
                        data=json.dumps(backend_settings))

    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))
    else:
        return resp


def delete_backend(name, domain, api_key=API_KEY):
    '''
    Takes (name, backend). Deletes a backend from the latest version of the service.
    '''
    service_id = get_service(name, api_key)["id"]
    service_version = get_service(name)["version"]
    requests.delete('https://api.fastly.com/service/{}/version/{}/backend/{}'.format(service_id,
                                                                                     service_version,
                                                                                     backend),
                    headers={"Fastly-Key": api_key,
                             "Accept": "application/json"
                            })


def clone_service(name, api_key=API_KEY):
    '''
    Clone the lastest service version.
    '''
    service_id = get_service(name, api_key)["id"]
    service_version = get_service(name, api_key)["version"]
    resp = requests.put('https://api.fastly.com/service/{}/version/{}/clone'.format(service_id,
                                                                                    service_version),
                        headers={"Fastly-Key": api_key,
                                 "Accept": "application/json",
                                })
    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))
    else:
        return resp.json()


def activate_service(name, service_version=None, api_key=API_KEY):
    '''
    Activate a service identified by name and number.
    '''
    service = get_service(name, api_key)
    service_id = service["id"]
    if not service_version:
        service_version = service["version"]
    resp = requests.put('https://api.fastly.com/service/{}/version/{}/activate'.format(service_id,
                                                                                    service_version),
                        headers={"Fastly-Key": api_key,
                                 "Accept": "application/json",
                                })

    if resp.status_code != 200:
        raise FastlyException("Error from Fastly API: {}".format(resp.text))
    else:
        return resp


def create_token(name,
                 username,
                 password):
    '''
    Create an API Token for the given service name. This will have access
    only to the provided service.
    '''
    if '/' in username:
        username = username.split('/')[1]
    if not password:
        password = get_pass()
    token = requests.post('https://api.fastly.com/tokens',
                         headers={"Fastly-Key": API_KEY,
                                  "Content-Type": "application/json",
                                  "Accept": "application/json"
                                  },
                         data=json.dumps({"service_id": get_service(name)["id"],
                                          'username': username,
                                          'password': password}))

    if token.status_code == 200:
        return token.json()["access_token"]
    else:
        print("Failed to create token")
        return token


def get_token(service_name, api_key=API_KEY):
    '''
    Get the token for a service by service name.
    '''
    service = get_service(service_name)
    tokens = requests.get('https://api.fastly.com/tokens',
                         headers={
                              "Fastly-Key": API_KEY,
                              "Accept": "application/json"
                         })
    return tokens


def parse_args(args):
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', help='Name of the service.')
    parser.add_argument('--vcl', help='Location of VCL.')
    parser.add_argument('--key', help='API key.')
    parser.add_argument('--cert', help='Location of cert.')
    parser.add_argument('--backend', help='URL of backend.')
    parser.add_argument('--domain', help='Fully Qualified Domain Name.')
    parser.add_argument('--modify', default=True, help='flag to modify an existing service; options are --vcl, --domain, and --backend', nargs='?', const=True)
    parser.add_argument('--activate', default=True, help='Whether to activate the new service. Defaults to True. Valid Inputs are 0 and 1.')
    return  parser.parse_args(args)


def main(args):
    '''
    Takes output of parse_args and runs main command line script.
    '''
    if not args.name:
        raise UsageException("See help by using the --help flag. Or visit https://lab.plat.farm/r0fls/pe-automation/tree/master/fastly".format())

    if not 'API_KEY' in vars() and not args.key:
        raise AuthException("Set the FASTLY_API_KEY environment variable or pass it in to the CLI with --key <API_KEY>".format(__file__))

    if args.modify:
        # need to clone the latest service to modify it
        new_service = clone_service(args.name, api_key=args.key)
        # our new version number
        if new_service.status_code != '200':
            raise UsageException("Received error from Fastly: {}".format(
                new_service.text))
        version = new_service["number"]
        if args.backend:
            create_backend(args.name, args.backend, cert=args.cert, cert_domain=args.domain, service_version=version, api_key=args.key)
        if args.vcl:
            try:
                # try to delete the existing VCL
                delete_vcl(args.name, service_version=version, api_key=args.key)
            except:
                # there was nothing to delete
                pass
            upload_vcl(args.name, args.vcl, service_version=version, api_key=args.key)
        if args.domain:
            add_domain(args.name, args.domain, service_version=version, api_key=args.key)
        # activate the new service, after modifying it
        if args.activate:
            activate_service(args.name, service_version=version, api_key=args.key)
    else:
        print("See help by using the --help flag. Or visit https://lab.plat.farm/r0fls/pe-automation/tree/master/fastly".format())

if __name__ == "__main__":
    import sys
    args = parse_args(sys.argv[1:])
    main(args)
