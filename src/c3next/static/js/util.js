define(["jquery.min","ajax"], function ($, ajax) {
    function formdata_is_empty_p (formdata) {
	var first = formdata.entries().next();
	return (first['done']) && (typeof first['value'] === "undefined");
    }
    function populate_header () {
	ajax.get_json('server.json').then(function (server) {
	    document.getElementById("unit-id").textContent = server["listener_id"];
	    if (server["reset_required"] && !document.getElementById('reset_required')) {
		var form = document.createElement('form');
		form.setAttribute('id','reset_required');
		form.setAttribute('method', 'post');
		form.classList.add('navbar-form');
		form.classList.add('navbar-right');
		form.addEventListener('submit', reset_submit);
		var button = document.createElement('button');
		button.setAttribute('type', 'submit');
		button.setAttribute('id', 'reset_button');
		button.classList.add('btn');
		button.classList.add('btn-danger');
		button.innerText = "Reboot Required - Click Here";
		form.appendChild(button);
		var hidden = document.createElement('input');
		hidden.setAttribute('type', 'hidden');
		hidden.setAttribute('name', 'reset');
		hidden.setAttribute('value', '1');
		form.appendChild(hidden);
		document.getElementById('navbar').appendChild(form);
	    }
	});
    }
    function form_url_encode (str) {
	return encodeURIComponent(str).replace("%20","+");
    }
    function form_tuple_encode (tuple) {
	return form_url_encode(tuple[0])+"="+form_url_encode(tuple[1]);
    }
    function form_encode (formdata) {
	var form_strings = [];
	for (var tuple of formdata.entries()) {
	    form_strings.push(form_tuple_encode(tuple));
	}
	return form_strings.join("&");
    }
    function util_alert (string, success) {
	var main_div = document.getElementById("navbar");
	var alert_div = document.createElement("div");
	alert_div.setAttribute("role", "alert");
	alert_div.classList.add("alert", "alert-dissmissable");
	alert_div.style.display = "none";
	if (success) {
	    alert_div.classList.add("alert-success");
	} else {
	    alert_div.classList.add("alert-danger");
	}
	alert_div.innerHTML = "<a href=\"#\" class=\"close\" data-dismiss=\"alert\" aria-label=\"close\">&times;</a>";
	alert_div.innerHTML += string
	main_div.insertBefore(alert_div, main_div.firstChild);
	//window.scrollTo(0,0);
	$(alert_div).slideDown("slow");
	window.setTimeout(function() {
	    $(alert_div).slideUp("slow");
	}, 5000);
    }
    function reset_submit (evt) {
	evt.preventDefault();
	var data = new FormData(document.getElementById('reset_required'));
	button_animation(0);
	ajax.post("", form_encode(data)).then(function(resp) {
	    window.setTimeout(reset_wait, 5000);
	});
    }
    function reset_wait () {
	ajax.get_json('server.json').then(
	    function success() {
		document.location = '/';
	    }, function fail() {
		window.setTimeout(reset_wait, 1000);
	    });
    }
    function button_animation (count) {
	var btn = document.getElementById('reset_button');
	var btn_txt = "Rebooting";
	for (var i = 0; i < count % 4; i++) {
	    btn_txt += '.';
	}
	btn.innerText = btn_txt;
	btn.style.width = '100px';
	window.setTimeout(button_animation, 1000, ++count);
    }
    return {
	"form_encode": form_encode,
	"alert": util_alert,
	"populate_header": populate_header,
	"formdata_empty": formdata_is_empty_p,
	"reset_wait": reset_wait
    }
});
