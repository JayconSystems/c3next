define(function() {
    var prefix='';
    'use strict';
    function request(method, url, data, json_p) {
	var promise = new Promise(function(resolve, reject) {
	    var req = new XMLHttpRequest();
	    req.open(method, prefix+url);
	    if (json_p == true) {
		if (data) {
		    data = JSON.stringify(data);
		} else {
		    data = "";
		}
		req.setRequestHeader('Content-Type', 'application/json');
	    } else {
		if (method == "POST") {
		    req.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
		}
	    }
	    req.onload = function() {
		if (req.status >= 200 && req.status <= 300) {
		    if (req.status != 204 && req.status != 201) {
			if (json_p) {
			    resolve(JSON.parse(req.response));
			} else {
			    resolve(req);
			}
		    } else {
			resolve(null);
		    }
		}
		else {
		    reject(req.response);
		}
	    };
	    req.onerror = function() {
		reject(Error("Network Error"));
	    };
	    req.send(data);
	});
	return promise;
    };
    return {
	'post': function(url, data) {
	    return request('POST', url, data, false);
	},
	'get': function(url) {
	    return request('GET', url);
	},
	'put': function(url, data) {
	    return request('PUT', url, data);
	},
	'delete': function(url) {
	    return request('DELETE', url);
	},
	'post_json': function(url, data) {
	    return request('POST', url, data, true);
	},
	'put_json': function(url, data) {
	    return request('PUT', url, data, true);
	},
	'get_json': function(url) {
	    return request('GET', url, undefined, true);
	}
    }
});
