define(['ajax','util','forms'], function (ajax, util, form_handler) {
    'use static';
    function show_hide_static_options () {
	var select = document.getElementById('proto');
	var static_options_div = document.getElementById('static_options');
	if (select.value == "dhcp") {
	    static_options_div.style.display = "none";
	} else {
	    static_options_div.style.display = "initial";
	}
    }

    function track_wired_type () {
	/* Hide and show the extended options for static ip, only if
	 * the static option is selected in the #proto select tag */
	var select = document.getElementById('proto');
	select.addEventListener("change", show_hide_static_options);
    }

    function main () {
	var wired_form_map = {
	    "ipaddr": form_handler.field.valid_ip,
	    "netmask": form_handler.field.valid_mask,
	    "gateway": form_handler.field.valid_ip,
	    "dns": form_handler.field.valid_dns,
	};
	form_handler.register("wired-form", wired_form_map);
	ajax.get_json('network.json').then(function (net) {
	    form_handler.fill("wired-form", net["wired"]);
	});

	var wireless_form_map = {
	    "wpa_key": form_handler.field.valid_wpa_key
	};
	form_handler.register("wireless-form", wireless_form_map);
	ajax.get_json('network.json').then(function (net) {
	    form_handler.fill("wireless-form", net["wireless"]);
	    show_hide_static_options();
	});

	// Register the handler anyway, for button handling, submission, &
	// filling
	form_handler.register("server-form", {});
	ajax.get_json('server.json').then(function (server) {
	    form_handler.fill("server-form", server);
	});

	util.populate_header();
	track_wired_type();
    }

    main();
});
