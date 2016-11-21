define(["ajax", "util"], function (ajax, util) {
    function valid_ip (el) {
	return valid_ip_noel(el.value);
    }
    function valid_ip_noel (ip) {
	var octets = ip.split('.');
	if (octets.length != 4) {
	    return false;
	}
	for (var i = 0; i < octets.length; i++) {
	    if (!(/^[0-9]{1,3}$/.test(octets[i]))) {
		return false;
	    }
	    var tmp = parseInt(octets[i])
	    if (tmp > 255) {
		return false
	    }
	}
	return true;
    }
    function valid_mask (el, evt) {
	var mask_l = el.value.split(".").length;
	if (mask_l == 4) {
	    return valid_ip(el);
	}
	if (mask_l == 1) {
	    var mask = parseInt(el.value);
	    if (mask < 0 || mask > 32) {
		return false;
	    }
	    /* Normalize bitmask to octets for uci, only after user is done with input */
	    if (evt && evt.type == "change") {
		el.value = maskbits_to_octets(parseInt(el.value));
		return valid_ip(el);
	    }
	}
	return false;
    }
    function maskbits_to_octets (mask) {
	var mask_octets = [0, 0, 0, 0];
	for (var byte_count = 0; mask > 0;) {
	    for (var bit_count = 7; bit_count >= 0 && mask > 0; mask--) {
		mask_octets[byte_count] += (1 << bit_count);
		bit_count -= 1;
	    }
	    byte_count += 1;
	}
	return mask_octets.join(".")
    }
    function valid_dns(el) {
	var ips = el.value.split(',');
	var r_list = [];
	if (ips.length > 3) {
	    return false;
	}
	for (var i = 0; i < ips.length; i++) {
	    r_list.push(valid_ip_noel(ips[i]));
	}
	return r_list.reduce(function (prev, cur) {
	    return (prev && cur);
	}, true);
    }

    function register_form_validator (form_el_id, field_valid_map) {
	var form = document.getElementById(form_el_id);
	form.addEventListener("submit", function (evt) {
	    return validate_form(form, field_valid_map, evt);
	});
	form.addEventListener("input", function (evt) {
	    validate_form(form, field_valid_map);
	});
	form.addEventListener("change", function (evt) {
	    validate_form(form, field_valid_map, evt);
	});
    }

    function valid_wpa_key (el) {
	var key_l = el.value.length;
	var valid_hex = /^[0-9a-fA-F]$/
	if (key_l < 8 || key_l > 64) {
	    return false;
	}
	if (key_l == 64) {
	    for (var i = 0; i < key_l; i++) {
		if (!valid_hex.test(el.value[i])) {
		    return false;
		}
	    }
	}
	return true;
    }

    var filled_values = {};

    function validate_form (form, field_valid_map, evt) {
	var r_list = [];
	var els = form.getElementsByTagName('input')
	for (var i = 0, l = els.length; i < l; i++) {
	    var el = els[i];
	    var r = true;
	     if (evt && evt.type == "change") {
		if (el.value == "" && el.getAttribute("default")) {
		    el.value = el.getAttribute("default");
		}
	    }
	    if (field_valid_map.hasOwnProperty(el.name)) {
		r = field_valid_map[el.name](el, evt);
	    } else {
		r = el.validity.valid
	    }
	    if (!r) {
		el.parentElement.classList.add('has-error');
	    } else {
		el.parentElement.classList.remove('has-error');
	    }
	    r_list.push(r);
	}
	var valid = r_list.reduce(function (prev, cur) {
		return prev && cur;
	}, true);

	/* Prepopulate formdata, even if unposted to detect actual changes to form */
	var data = new FormData(form);
	if (filled_values.hasOwnProperty(form.getAttribute('id'))) {
	    var prev_values = filled_values[form.getAttribute('id')];
	    for (var field in prev_values) {
		if (prev_values.hasOwnProperty(field)) {
		    var field_vals = data.getAll(field);
		    if (field_vals.length > 1) {
			if (field_vals == prev_values[field]) {
			    data.delete(field);
			}
		    } else {
			if (field_vals[0] == prev_values[field]) {
			    data.delete(field);
			}
		    }
		}
	    }
	}

	if (evt && evt.type == "submit") {
	    /* If we're executing js, try to do nice async POSTS, w/o
	     * js fallback to form post w/o client-side validation */
	    evt.preventDefault();
	    if (valid) {
		if (!util.formdata_empty(data)) {
		    ajax.post("", util.form_encode(data)).then(function(resp) {
			var button = form.getElementsByTagName("button")[0];
			button.textContent = "Saved";
			button.setAttribute("disabled", "disabled");
			util.populate_header();
		    });
		}
	    }
	} else {
	    var button = form.getElementsByTagName("button")[0];
	    if (valid) {
		if (!util.formdata_empty(data)) {
		    button.textContent = "Save Changes";
		    button.removeAttribute("disabled");
		} else {
		    button.textContent = "No Changes";
		    button.setAttribute("disabled", "disabled");
		}
	    } else {
		button.textContent = "Fix Errors";
		button.setAttribute("disabled", "disabled");
	    }
	}
	return valid;
    }

    function fill_form (form_id, obj) {
	var form = document.getElementById(form_id);

	var slice = Array.prototype.slice;
	var inputs = slice.call(form.getElementsByTagName("input"));
	inputs = inputs.concat(slice.call(form.getElementsByTagName("select")));
	for (var i = 0; i < inputs.length; i++) {
	    if (obj.hasOwnProperty(inputs[i].name)) {
		inputs[i].value = obj[inputs[i].name];
	    }
	}
	/* Cache previous values so we can send only changes */
	filled_values[form_id] = obj;
    }
    return {
	"register": register_form_validator,
	"fill": fill_form,
	"field": {
	    "valid_ip": valid_ip,
	    "valid_mask": valid_mask,
	    "valid_dns": valid_dns,
	    "valid_wpa_key": valid_wpa_key
	}
    }
});
