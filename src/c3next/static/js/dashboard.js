define(['ajax','util'], function(ajax, util) {
    'use strict';
    function update_beacon_table (beacons) {
	var table = document.getElementById('beacons_table');
	var old_tbody = table.getElementsByTagName('tbody')[0];
	var new_tbody = document.createElement('tbody');
	for (var i = 0, l = beacons.length; i < l; i++) {
	    var beacon = beacons[i];
	    var row = document.createElement('tr');
	    if (beacon.hasOwnProperty("mac")) {
		row.innerHTML += "<td>"+beacon.mac+" (secure)</td>";
	    } else {
		row.innerHTML += "<td>Maj:"+beacon.major+" / Min:"+beacon.minor+"</td>";
	    }
            row.innerHTML += "<td>"+Math.round(beacon.distance*100)/100+"m</td>";
	    row.innerHTML += "<td>"+Math.round(beacon.error*100)/100+"m</td>";
	    new_tbody.appendChild(row);
	}
	table.replaceChild(new_tbody, old_tbody);
	window.setTimeout(fetch_beacons, 2500);
    }
    function fetch_beacons() {
	ajax.get_json('beacons.json').then(update_beacon_table, function (resp) {
	    console.log("Failed to get recent beacons:", resp);
	    window.setTimeout(fetch_beacons, 5000);
	});
    }

    function fetch_last_ack() {
	ajax.get_json('server.json').then(
	    function (svr) {
		document.getElementById(
		    "last_ack").innerHTML = svr['last_ack'];
		window.setTimeout(fetch_last_ack, 1500);
	    },
	    function (resp) {
		console.log("Failed to get server.json:", resp);
		window.setTimeout(fetch_last_ack, 5000);
	    });
    }



    function pretty_print_uci_key (key) {
	var map = {
	    "ifname": "Interface",
	    "proto": "IP Type",
	    "ipaddr": "IP Address",
	    "netmask": "Netmask",
	    "gateway": "Gateway",
	    "dns": "DNS Servers",
	    "device": "Device",
	    "network": "Network",
	    "mode": "Mode",
	    "ssid": "SSID",
	    "encryption": "Encryption"};
	if (map.hasOwnProperty(key)) {
	    return map[key];
	}
	return key;
    }

    function populate_netstatus () {
	ajax.get_json('network_status.json').then(
	    function (net) {
		for (var type in net) {
		    if (net.hasOwnProperty(type)) {
			var dl = document.getElementById(type+"_status");
			dl.innerHTML = "<dt>Not Connected</dt>";
			for (var prop in net[type]) {
			    if (dl.innerHTML === "<dt>Not Connected</dt>") {
				dl.innerHTML = "";
			    }
			    if (net[type].hasOwnProperty(prop)){
				dl.innerHTML += "<dt>"+pretty_print_uci_key(prop)+"</dt>";
				dl.innerHTML += "<dd>"+net[type][prop]+"</dd>";
			    }
			}
		    }
		}
		var wireless_status = document.getElementById('wireless_status');

	    },
	    function (resp) {
	    });
    }
    function populate_svrstatus () {
	ajax.get_json('server.json').then(function (server) {
	    var dl = document.getElementById("server_status");
	    dl.innerHTML = "<dt>Hostname</dt><dd>"+server["server"]+"</dd>";
	    dl.innerHTML += "<dt>Last ACK</dt><dd id=\"last_ack\">"+server["last_ack"]+"</dd>";
	});
    }
    // util.populate_header();
    // populate_netstatus();
    // populate_svrstatus();
    // fetch_beacons();
    // fetch_last_ack();
});
