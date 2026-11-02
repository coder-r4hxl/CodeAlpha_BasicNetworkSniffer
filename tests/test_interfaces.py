import sys
import pytest
from unittest.mock import patch, MagicMock

import sniffer
from sniffer import (
    get_interface_details,
    format_interfaces_output,
    validate_interface,
    parse_args,
)


def test_get_interface_details_success():
    mock_dev = MagicMock()
    mock_dev.name = "eth0"
    mock_dev.description = "Ethernet Adapter"
    mock_dev.index = 2
    mock_dev.mac = "00:11:22:33:44:55"
    mock_dev.ip = "192.168.1.100"
    mock_dev.ips = {4: ["192.168.1.100"], 6: ["fe80::1"]}
    mock_dev.status = "up"

    with patch("sniffer.get_if_list", return_value=["eth0"]), \
         patch.object(sniffer.conf, "ifaces", {"eth0": mock_dev}):
        details = get_interface_details()
        assert len(details) == 1
        d = details[0]
        assert d["name"] == "eth0"
        assert d["description"] == "Ethernet Adapter"
        assert d["index"] == 2
        assert d["mac"] == "00:11:22:33:44:55"
        assert d["ipv4"] == "192.168.1.100"
        assert d["ipv6"] == "fe80::1"
        assert d["status"] == "up"


def test_get_interface_details_missing_metadata():
    with patch("sniffer.get_if_list", return_value=["dummy0"]), \
         patch.object(sniffer.conf, "ifaces", {}):
        details = get_interface_details()
        assert len(details) == 1
        d = details[0]
        assert d["name"] == "dummy0"
        assert d["description"] == "unavailable"
        assert d["index"] == "unavailable"
        assert d["mac"] == "unavailable"
        assert d["ipv4"] == "unavailable"
        assert d["ipv6"] == "unavailable"
        assert d["status"] == "unavailable"


def test_get_interface_details_empty():
    with patch("sniffer.get_if_list", return_value=[]):
        details = get_interface_details()
        assert details == []
        formatted = format_interfaces_output(details)
        assert formatted == "No network interfaces found."


def test_format_interfaces_output_multiple():
    ifaces = [
        {
            "name": "eth0",
            "description": "Ethernet",
            "index": 1,
            "mac": "00:00:00:00:00:01",
            "ipv4": "10.0.0.1",
            "ipv6": "fe80::1",
            "status": "up",
        },
        {
            "name": "lo",
            "description": "Loopback",
            "index": 2,
            "mac": "00:00:00:00:00:00",
            "ipv4": "127.0.0.1",
            "ipv6": "::1",
            "status": "up",
        },
    ]
    formatted = format_interfaces_output(ifaces)
    assert "[1] Name: eth0" in formatted
    assert "[2] Name: lo" in formatted
    assert "IPv4 Address: 10.0.0.1" in formatted


def test_validate_interface_valid():
    with patch("sniffer.get_if_list", return_value=["eth0", "lo"]):
        assert validate_interface("eth0") is True
        assert validate_interface(None) is True


def test_validate_interface_invalid(capsys):
    with patch("sniffer.get_if_list", return_value=["eth0", "lo"]):
        with pytest.raises(SystemExit) as excinfo:
            validate_interface("nonexistent_iface")
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: invalid interface 'nonexistent_iface'." in captured.out


def test_validation_occurs_before_sniff():
    with patch("sniffer.get_if_list", return_value=["eth0"]), \
         patch("sniffer.sniff") as mock_sniff:
        with pytest.raises(SystemExit) as excinfo:
            with patch("sys.argv", ["sniffer.py", "-i", "bad_iface"]):
                sniffer.main()
        assert excinfo.value.code == 1
        mock_sniff.assert_not_called()


def test_list_interfaces_cli(capsys):
    with patch("sniffer.get_if_list", return_value=["eth0"]), \
         patch("sniffer.sniff") as mock_sniff:
        with pytest.raises(SystemExit) as excinfo:
            with patch("sys.argv", ["sniffer.py", "--list-interfaces"]):
                sniffer.main()
        assert excinfo.value.code == 0
        mock_sniff.assert_not_called()
        captured = capsys.readouterr()
        assert "Available Network Interfaces:" in captured.out
        assert "Name: eth0" in captured.out


def test_get_interface_details_api_error(capsys):
    with patch("sniffer.get_if_list", side_effect=OSError("Device query failed")):
        with pytest.raises(SystemExit) as excinfo:
            get_interface_details()
        assert excinfo.value.code == 1
        captured = capsys.readouterr()
        assert "Error: failed to enumerate network interfaces" in captured.out
