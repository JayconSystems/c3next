define(["ajax"], function (ajax) {
    'use strict';

    function del_obj(evt) {
	if (evt.target.hasAttribute('id') &&
	    evt.target.classList.contains('delete')) {
	    console.log("Trying to delete: ", evt);
	    ajax.delete(location.pathname + '/' + evt.target.id).then(
		function() {
		    location = location;
		});
	}
    }
    var tab = document.getElementById('obj_list');
    tab.addEventListener('click', del_obj);

});
