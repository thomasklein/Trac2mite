$(window).load(function(){
	
	MITE.init();
});

var MITE = function() {
	
//############	
// private VARS
//#######	
	
	// contains projects and services of the user
	var go_user_rsrcs = {p : Array(), s : Array()};
	var go_user_values = {};
	var go_labelTexts = {"rsrc_p" : "<em>mite</em>.project", 
						"rsrc_s" : "<em>mite</em>.service",
						"add_to_mite" : "[+]",
						"none" : "...",
						"click_to_change" : "Click to change",
						"click_to_add_p" : "Click to select one of your mite.projects " + 
										   "and synchronize this time entry with your mite.account.",
						"click_to_add_s" : "Click to select one of your mite.services " + 
										   "and synchronize this time entry with your mite.account."};
	var gi_maxLengthLinks = 30;				

//############	
// private METHODS
//#######

/*********************************************************
 * Fetches the users mite resources (projects and services) published by the plugin 
 * in <link>-Tags in the document header and deletes those references from the DOM 
 */
var initMiteResources = function() {
	
	// get reference to head tag to remove child elements
	var o_head_tag = $("head")[0];
	
	$("link").each(function() {
		
		if (this.type=="trac2miteRsrc") {
			
			go_user_rsrcs[this.className].push([this.rel, this.title]);
			
		// delete DOM node
			o_head_tag.removeChild(this);
		}
		else if(this.type=="trac2miteValue") {
			
		// get id of the mite resource
			var i_id = this.rel.substring(this.rel.indexOf("_") + 1);
			
		// init time entry in container
			if (!go_user_values[this.title])
				go_user_values[this.title] = {'p' : null, 's' : null};
		
			if (i_id)
				go_user_values[this.title][this.className] = i_id;
			
		// delete DOM node	
			o_head_tag.removeChild(this);
		}
	});
}//initMiteResources


/*********************************************************
 * Get the current page name of the TracHoursPlugin to decide, which components to add
 */ 
	var initMiteComponentsHours = function () {
		
		var miteContainer = $('<div/>');
		miteContainer.css({'display' : 'block', 'padding':'0.5em 0'});
		
		var containerRsrcs = getMiteResources_f();
		
		for(var type in containerRsrcs){
			// use a a copy of the container elements 
			// to prevent obfuscation with bounded event handler
			miteContainer.append(containerRsrcs[type].clone());
		}
		
		miteContainer.append($('<div style="clear:both" />'));
		
		// append mite components beneath the date input fields
		miteContainer.insertAfter('[name=year] + br');
		
		//#######################
		// build mite components for existing time entries
		containerRsrcs = getMiteResources_f(true);
		
		var newRowHeaders = $('<th>' + go_labelTexts['rsrc_s'] + '</th>' +
							  '<th>' + go_labelTexts['rsrc_p'] + '</th>');
		
		// insert new row headers for mite components after table cell header 'Hours worked' 
		newRowHeaders.insertAfter("th:contains('Hours worked')");
		
		var ao_rows = $('.listing.reports').find("tr"); //get all rows of the time table
		var i_counter = 1;//leave out first row since this is the table header
		
		$('.listing.reports').find("input[name^='hours']").each(function() {
			
			// get the local id of the current time entry 
			var i_id = this.name.substring(this.name.indexOf("_") + 1);
			var i_numberAddedRows = 0;
			
			// reset width of the time imput components
			$(this).css({'width':'25px'});
			$(this).next().css({'width':'25px'});
			
			for(var type in containerRsrcs){
				
				var $o_newColumn = $('<td />');
				
			// init vars with default values	
				var s_linkName = go_labelTexts['none'];
				var s_linkTitle = go_labelTexts['click_to_change'];
				var $o_container = createNewRsrcSelectBox(containerRsrcs[type].clone(), i_id, type);
				
				if (go_user_values[i_id]) {
					
					if (go_user_values[i_id][type]) {
						
						var $o_entry = $o_container.find("select option[value=" + go_user_values[i_id][type] + "]");
						
					// in case a formerly selected mite resource is longer set as a preference	
						if ($o_entry.length > 0) {
							$o_entry.attr({'selected':'selected'});
							s_linkName = $o_entry.text();
							s_linkTitle = go_labelTexts['click_to_change'];

							// shorten link title if too long
							if (s_linkName.length > gi_maxLengthLinks) {
								s_linkName = s_linkName.substring(0, gi_maxLengthLinks) + "...";
							}
						}
					}
				}
				else {
					s_linkName = go_labelTexts['add_to_mite'];
					s_linkTitle = go_labelTexts['click_to_add_' + type];
				}
							
				var $o_linkShowMiteField = $('<a title="' + s_linkTitle + '" href="#">' + s_linkName + '</a>');
				
				$o_newColumn.append($o_linkShowMiteField);
				$o_newColumn.append($o_container);
				
				// insert the table cells after the cell for "hours worked"
				$o_newColumn.insertAfter($(ao_rows[i_counter].cells[(1 + i_numberAddedRows)]));
				i_numberAddedRows++;
				
				// show select box when resource link gets clicked
				$o_linkShowMiteField.click(function(e) {
					e.preventDefault();
					$(this).next('div').show();
					$(this).hide();
					return false;
				});
			}
			
			i_counter++;
		});
		
		return true;
	}//initMiteComponentsHours
	
	
	var createNewRsrcSelectBox = function($o_container, i_timeEntryId, s_rsrcType) {
		
		$o_container.css({'display' : 'none'});
		var $o_rsrc_selectBox = $o_container.find("select");
		
		// set specific id and name for select box
		$o_rsrc_selectBox.attr({"id":"mite_" + s_rsrcType + "_id" + i_timeEntryId,
							 	"name":"mite_" + s_rsrcType + "_id" + i_timeEntryId});
		
		return $o_container;
		
	}//createNewRsrcSelectBox
		
/*****************************************************
 * Returns an array containing a select box with mite resources 
 * for each type (projects and services).
 * If the param b_noLabels is set, also add a label in front of each select box
 */	
	var getMiteResources_f = function(b_noLabels) {

	//#######################
	// build mite components for new time entry 
		var containerRsrcs = {};

		for(var type in go_user_rsrcs){

			// create a select box filled with resources
			var selectBoxRsrc = $('<select id="mite_' + type + '_id" name="mite_' + type + '_id" />');
			
			var tmp_option = '<option value="">...</option>';
			selectBoxRsrc.append(tmp_option);

			for (var i = 0; i < go_user_rsrcs[type].length; i++) {

				tmp_option = '<option value="' + go_user_rsrcs[type][i][0] + '">' +
							 go_user_rsrcs[type][i][1]+ '</option>';

				selectBoxRsrc.append(tmp_option);
			}

			containerRsrcs[type] = $('<div />');

			if (b_noLabels === undefined) {
				containerRsrcs[type].css({'float' : 'left', 'padding-right':'1em'});
				
				// create a label for it
				var labelRsrc = $('<label for="mite_' + type + '_id"/>');
				labelRsrc.html(go_labelTexts["rsrc_" + type] + ": ");
				labelRsrc.appendTo(containerRsrcs[type]);
			}

			selectBoxRsrc.appendTo(containerRsrcs[type]);
		}
		return containerRsrcs;
	}//getMiteResources_f
	
	
/*****************************************************
 * Add onClick behaviors to buttons in the mite preferences
 */	
	var initMiteComponentsPreferences = function() {
		
		// save selectors
		$o_btnCheckAccountData = $('#check_account_data');
		$o_btnDisAccountData = $('#disconnect_account_data');
		$o_btnSavePreferences = $('#save_preferences');
		$o_nameButtonPressed = $('#mite_button_pressed');
		$o_miteNotifier = $('#mite_notifier_account_data');
		$o_miteNotifier = $('.mite_notifier');
		$o_linkChangeApiKey = $('#mite_link_change_api_key');
		$o_fieldApiKey = $('#mite_api_key');
		
		fn_btnClickHandler = function(current) {
			$(current).css('cursor', 'wait');
			$(current).attr('disabled', true);
			
			$o_miteNotifier.each(function() {
				$(this).css('display', 'block');
			});
			
			$o_nameButtonPressed.val($(current).attr('name'));
			$o_btnDisAccountData.attr('disabled', true);
			$o_btnCheckAccountData.attr('disabled', true);
			$o_btnSavePreferences.attr('disabled', true);
			
			current.form.submit();
		}
		
		$o_btnCheckAccountData.click(function(e) {
			fn_btnClickHandler(this);
			return true;
		});
		
		$o_btnDisAccountData.click(function(e) {
			if (confirm('Are you sure you want to disconnect your mite.account? Time entries in mite and Trac will still be available afterwards. In Trac will be deleted your: \n - mite account data \n - imported mite.projects and mite.services')) {
				fn_btnClickHandler(this);
				return true;
			}
			else return false;
		});
		
		$o_btnSavePreferences.click(function(e) {
			fn_btnClickHandler(this);
			return true;
		});
		
		
		$o_linkChangeApiKey.click(function(e) {
			$o_fieldApiKey.clone()
						  .attr({readonly:'',type:'text'})
						  .removeClass()
						  .replaceAll($o_fieldApiKey)
						  .val('');//delete
			
		});
	}//initMiteComponentsPreferences
	
	
/*****************************************************
 * Check for TracHours components by their tag name
 */
	var hasTracHoursPluginComponents = function() {
		
		return (($('[name=year]').length==1) && ($('[name=month]').length==1) && ($('[name=day]').length==1));
	}//hasTracHoursPluginComponents
	

/*****************************************************
 * Check for TracHours components
 */
	var initMiteComponentsTicketSidebar = function() {
		
		var miteContainer = $('<div/>');
		miteContainer.css({'display' : 'block', 'padding':'0.5em 1em'});
		
		var containerRsrcs = getMiteResources_f();
		
		for(var type in containerRsrcs){
			// use a a copy of the container elements 
			// to prevent obfuscation with bounded event handler
			containerRsrcs[type].clone().appendTo(miteContainer);
		}
		
		var floatBreaker = $('<div style="clear:left" />');
		floatBreaker.appendTo(miteContainer);
		
		// append mite components beneath the date input fields
		miteContainer.insertAfter('.sidebar center');
	}//initMiteComponentsTicketSidebar
	
	
//############	
// public METHODS
//#######	
	return {
		
	/*********************************************************
	* Init mite stuff needed for the current page
	*/
		init : function () {
			
			initMiteResources()
			
		// for component ITicketSidebarProvider
			if ($('.sidebar center').length > 0) {
				initMiteComponentsTicketSidebar();
			}
		// requests going to "mite" tab in the user preferences	
			else if ($('#tab_mite').length > 0) {
				initMiteComponentsPreferences();
			}
		// requests going to /hours/<ticket-id>
			else if (hasTracHoursPluginComponents()) {
				initMiteComponentsHours();
			}
			
		},//init
	};//END of MITE return values	
}();//execute function instantly to return the object in the global namespace	