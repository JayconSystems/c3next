define(["ajax","forms","util"], function (ajax, form_handler, util) {
    'use strict';

    /* No specific field validation functions needed, the form_handler
     * will check the input field validation attributes. The handler
     * also does button mgmt., async posts */
    form_handler.register("server-form", {});
    ajax.get_json('server.json').then(function (server) {
	form_handler.fill("server-form", server);
    });

    /* Update the listener_id in the header */
    util.populate_header();

});
