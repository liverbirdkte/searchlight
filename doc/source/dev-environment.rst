..
    c) Copyright 2015 Hewlett-Packard Development Company, L.P.

    Licensed under the Apache License, Version 2.0 (the "License"); you may
    not use this file except in compliance with the License. You may obtain
    a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
    License for the specific language governing permissions and limitations
    under the License.

***********************
Development Environment
***********************

This guide will walk you through setting up a typical development
environment. You may set it up using devstack or manually.

.. _Devstack Development Environment:

Devstack Development Environment
++++++++++++++++++++++++++++++++

Please see: https://github.com/openstack/searchlight/tree/master/devstack

.. _Manual Development Environment:

Manual Development Environment
++++++++++++++++++++++++++++++

Prerequisites
=============

Install prerequisites::

    # Ubuntu/Debian:
    sudo apt-get update
    sudo apt-get install python-dev libssl-dev python-pip libxml2-dev \
                         libxslt-dev git git-review libffi-dev gettext \
                         python-tox

    # Fedora/RHEL:
    sudo yum install python-devel openssl-devel python-pip libxml2-devel \
                     libxslt-devel git git-review libffi-devel gettext

    # openSUSE/SLE 12:
    sudo zypper install git git-review libffi-devel \
                        libopenssl-devel libxml2-devel libxslt-devel \
                        python-devel python-flake8 \
                        python-nose python-pip python-setuptools-git \
                        python-testrepository python-tox python-virtualenv \
                        gettext-runtime

    sudo easy_install nose
    sudo pip install virtualenv setuptools-git flake8 tox testrepository

If using RHEL and yum reports "No package python-pip available" and "No
package git-review available", use the EPEL software repository. Instructions
can be found at `<http://fedoraproject.org/wiki/EPEL/FAQ#howtouse>`_.

You may need to explicitly upgrade virtualenv if you've installed the one
from your OS distribution and it is too old (tox will complain). You can
upgrade it individually, if you need to::

    sudo pip install -U virtualenv

This guide assumes that you also have the following services
minimally available:

* Elasticsearch (See :doc:`elasticsearch` for install information).
* Keystone

.. note::
   Some Elasticsearch installation methods may call for installing a
   headless JRE. If you are working on a desktop based OS (such as Ubuntu
   14.04), this may cause tools like pycharms to no longer launch.  You can
   switch between JREs and back: to a headed JRE version using:
   "sudo update-alternatives --config java".

Additional services required to be installed will depend on the plugins
activated in searchlight.

Installing Searchlight
======================

.. index::
   double: install; searchlight

1. Clone the Searchlight repo from GitHub

::

   $ mkdir openstack
   $ cd openstack
   $ git clone https://github.com/openstack/searchlight.git
   $ cd searchlight


2. Setup a virtualenv

.. note::
   This is an optional step, but will allow Searchlight's dependencies
   to be installed in a contained environment that can be easily deleted
   if you choose to start over or uninstall Searchlight.

::

   $ tox -evenv --notest

Activate the virtual environment whenever you want to work in it.
All further commands in this section should be run with the venv active:

::

   $ source .tox/venv/bin/activate

.. note::
   When ALL steps are complete, deactivate the virtualenv: $ deactivate

4. Install Searchlight and its dependencies

::

   (venv) $ python setup.py develop

5. Generate sample config.

::

   (venv) $ oslo-config-generator --config-file
   etc/oslo-config-generator/searchlight-api.conf

6. Create Searchlight's config files by copying the sample config files

::

   $ cd etc/
   $ ls *.sample | while read f; do cp $f $(echo $f | sed "s/.sample$//g"); done

7. Make the directory for Searchlight’s log files

::

   $ mkdir -p ../log

8. Make the directory for Searchlight’s state files

::

   $ mkdir -p ../state

Configuring Searchlight
=======================

.. index::
    double: configure; searchlight

Searchlight has several configuration files. The following are the basic
configuration suggestions.

Keystone integration
--------------------

Keystone integration should be set up for proper authentication and service
integration

.. toctree::
   :maxdepth: 2

   authentication

Other development environment configuration
-------------------------------------------

Additional development environment configuration items are specified below.

searchlight-api.conf
````````````````````
::

    [DEFAULT]
    debug = true
    verbose = true
    log_file = log/searchlight.log

Plugin Configuration
--------------------

The search service is driven using a plugin mechanism for integrating to other
services. Each integrated service may require additional configuration
settings. For example, typically, you will need to add the
``searchlight_indexer`` notification topic to each service's configuration.

See :ref:`searchlight-plugins` for plugin installation and general
configuration information.

See each plugin below for detailed information about specific plugins:


.. toctree::
   :maxdepth: 1
   :glob:

   plugins/*

Initialize the Elasticsearch Index
==================================

.. index::
   double: install; sync


Perform initial sync of the resources to Elasticsearch. All plugins for
searchlight must have their services installed and available at an endpoint
registered in keystone (e.g. glance).

::

   $ cd <install dir. eg: openstack/searchlight>

   # Make sure your virtualenv is sourced
   $ source .tox/venv/bin/activate

   # Run the index operation.
   (venv) $ searchlight-manage index sync

   # Alternatively, you can directly invoke the command using the following.
   (venv) $ python searchlight/cmd/manage.py --config-file etc/searchlight-api.conf index sync

This command may be re-run at any time to perform a full re-index.

Start Index Update Monitoring
=============================

The index is updated continually based on updates to the source resource
data. Start this service to start update monitoring. Note, depending on the
resource type, this will typically require that you have configured
notifications properly for the service which owns the resource (e.g. Glance
images).

::

   $ cd <install dir. eg: openstack/searchlight>

   # Make sure your virtualenv is sourced
   $ source .tox/venv/bin/activate

   # Start the index update monitoring.
   (venv) $ searchlight-listener

   # Alternatively, you can directly invoke the command using the following.
   (venv) $ python searchlight/cmd/listener.py --config-file
   etc/searchlight-api.conf

Initialize & Start the API Service
==================================

.. index::
   double: install; api

Open up a new ssh window and log in to your server (or however you’re
communicating with your server).

::

   $ cd <install dir. eg: openstack/searchlight>

   # Make sure your virtualenv is sourced
   $ source .tox/venv/bin/activate

   # Start the API Service.
   (venv) $ searchlight-api

   # Alternatively, you can directly invoke the command using the following.
   (venv) $ python searchlight/cmd/api.py --config-file etc/searchlight-api.conf

You should now see the log from the API service.


Exercising the API
==================

.. note:: If you have a firewall enabled, make sure to open port 9393.

Using a web browser, curl statement, or a REST client, calls can be made to the
Searchlight API using the following format where "api_version" is v1
and "command" is any of the commands listed under the :doc:`searchlightapi`

::

   http://IP.Address:9393/api_version/command

Example: List plugins::

   $ curl http://localhost:9393/v1/search/plugins

Example: List all data::

   # Prerequisite Setup:
   $ token=<insert token>
   $ touch search.json
   # Paste content
   {
     "query": {
       "match_all": {}
     },
     "limit": 1000
   }

   # Execute query
   $ curl -X POST http://localhost:9393/v1/search -H "X-Auth-Token:$token" \
   -d @search.json -H "Content-Type: application/json" | python -mjson.tool

You can find the IP Address of your server by running

::

   curl -s checkip.dyndns.org | sed -e 's/.*Current IP Address: //' -e 's/<.*$//'

Troubleshooting
===============

Elasticsearch:

You can directly connect to the Elasticsearch server and examine
its contents. We recommend using the Sense extension for google chrome.

Notifications:

Use rabbitmqctl to examine unconsumed notifications::

    sudo rabbitmqctl list_queues | grep info

Currently notifications from other services may be consumed by other
listeners and searchlight will not receive the notifications. This is
being investigated. This does mean that you can not currently use listener
based updates in an environment that has ceilometer deployed. You will need
to periodically perform a few full re-index operation.
