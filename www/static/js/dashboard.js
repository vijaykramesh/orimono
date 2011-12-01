// this is the dashboard onready js for Uzume Orimono
// most of the application is all ajax, so most everything
// is handled here in this one onready, with some additional
// functions to re-add bindings on newly initialized panes.

$(document).ready(function(){
    var opts = {
	lines: 12, // The number of lines to draw
	length: 7, // The length of each line
	width: 4, // The line thickness
	radius: 10, // The radius of the inner circle
	color: '#fff', // #rgb or #rrggbb
	speed: 1, // Rounds per second
	trail: 60, // Afterglow percentage
	shadow: false // Whether to render a shadow
    };
    var spinner = null;
    $('#loading')
	.hide()  // hide it initially
	.ajaxStart(function() {
	    $(this).show();
	    spinner = new Spinner(opts).spin($(this)[0]);
	})
	.ajaxStop(function() {
	    $(this).hide();
	    spinner.stop();
	});

    $('.local_mapping').bind('click', function(e){window.location = '/internal/?mapping_name=' + $(this).attr('mapping_name'); });
    $('.external_mapping').bind('click', function(e){window.location = '/external/?mapping_name=' + $(this).attr('mapping_name'); });

});
