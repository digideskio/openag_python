"""
Tests the ability to set up mirroring with a cloud server
"""
import mock

from click.testing import CliRunner
import requests_mock

from tests import mock_config

from openag.couchdb import Server
from openag.db_names import per_farm_dbs
from openag.cli.farm import show, create, list, init, deinit

@mock_config({
    "cloud_server": {
        "url": None
    }
})
def test_farm_without_cloud_server(config):
    runner = CliRunner()

    # Show -- Should raise an error because there is no cloud server
    res = runner.invoke(show)
    assert res.exit_code, res.output

    # Create -- Should raise an error because there is no cloud server
    res = runner.invoke(create)
    assert res.exit_code, res.output

    # List -- Should raise an error because there is no cloud server
    res = runner.invoke(list)
    assert res.exit_code, res.output

    # Init -- Should raise an error because there is no cloud server
    res = runner.invoke(init)
    assert res.exit_code, res.output

    # Deinit -- Should raise an error because there is no cloud server
    res = runner.invoke(deinit)
    assert res.exit_code, res.output

@mock_config({
    "cloud_server": {
        "url": "http://test.test:5984",
        "username": None,
        "password": None,
        "farm_name": None
    }
})
def test_farm_without_user(config):
    runner = CliRunner()

    # Show -- Should raise an error because no farm is selected
    res = runner.invoke(show)
    assert res.exit_code, res.output

    # Create -- Should raise an error because the user is not logged in
    res = runner.invoke(create)
    assert res.exit_code, res.output

    # List -- Should raise an error because the user is not logged in
    res = runner.invoke(list)
    assert res.exit_code, res.output

    # Init -- Should raise an error becuase the user is not logged in
    res = runner.invoke(init)
    assert res.exit_code, res.output

    # Deinit -- Should raise an error because no farm is selected
    res = runner.invoke(deinit)
    assert res.exit_code, res.output

@mock_config({
    "cloud_server": {
        "url": "http://test.test:5984",
        "username": "test",
        "password": "test",
        "farm_name": None
    },
    "local_server": {
        "url": None
    }
})
@requests_mock.Mocker()
def test_farm_with_only_cloud_server(config, m):
    runner = CliRunner()

    # Show -- Should raise an error because no farm is selected
    res = runner.invoke(show)
    assert res.exit_code, res.output

    # List -- Should raise an error because there are no farms yet
    m.get("http://test.test:5984/_all_dbs", text="[]")
    m.get("http://test.test:5984/_session", text="{}")
    m.get("http://test.test:5984/_users/org.couchdb.user%3Atest", text="{}")
    res = runner.invoke(list)
    assert res.exit_code, res.output

    # Create -- Should work
    m.post("http://test.test:5984/_openag/v0.1/register_farm", text="{}")
    res = runner.invoke(create, ["test"])
    assert res.exit_code == 0, res.exception or res.output

    # List -- Should output "test"
    m.get(
        "http://test.test:5984/_users/org.couchdb.user%3Atest",
        text='{"farms": ["test"]}'
    )
    res = runner.invoke(list)
    assert res.output == "test\n", res.output

    # Show -- Should raise an error because no farm is selected
    res = runner.invoke(show)
    assert res.exit_code, res.output

    # Init -- Should work
    res = runner.invoke(init, ["test"])
    assert res.exit_code == 0, res.exception or res.output

    # Show -- Should work and output "test"
    res = runner.invoke(show)
    assert res.exit_code == 0, res.exception or res.output

    # List -- Should have an asterisk before "test"
    res = runner.invoke(list)
    assert res.output == "*test\n", res.exception or res.output

    # Deinit -- Should work
    res = runner.invoke(deinit)
    assert res.exit_code == 0, res.exception or res.output

    # Show -- Should raise an error because no farm is selected
    res = runner.invoke(show)
    assert res.exit_code, res.output

    # List -- Should work and output "test"
    res = runner.invoke(list)
    assert res.output == "test\n", res.exception or res.output

@mock_config({
    "cloud_server": {
        "url": "http://test.test:5984",
        "username": "test",
        "password": "test",
        "farm_name": None
    },
    "local_server": {
        "url": "http://localhost:5984"
    }
})
@mock.patch.object(Server, "replicate")
@mock.patch.object(Server, "cancel_replication")
@requests_mock.Mocker()
def test_farm_with_cloud_and_local_server(
    config, cancel_replication, replicate, m
):
    runner = CliRunner()

    # Init -- Should replicate per farm DBs
    m.get("http://localhost:5984/_all_dbs", text="[]")
    res = runner.invoke(init, ["test"])
    assert res.exit_code == 0, res.exception or res.output
    assert replicate.call_count == len(per_farm_dbs)
    replicate.reset_mock()

    # Deinit -- Should cancel replication of per farm DBs
    res = runner.invoke(deinit)
    assert res.exit_code == 0, res.exception or res.output
    assert cancel_replication.call_count == len(per_farm_dbs)