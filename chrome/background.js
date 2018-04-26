// Chrome - Get selected text and send to server
// http://vikku.info/programming/chrome-extension/get-selected-text-send-to-web-server-in-chrome-extension-communicate-between-content-script-and-background-page.htm
var request_data = null;
 
chrome.extension.onRequest.addListener(function(request, sender, sendResponse)
{
    switch(request.message)
    {
        case 'sendBlock':
            window.request_data = request.data
        break;
         
        default:
            sendResponse({data: 'Invalid arguments'});
        break;
    }
	console.log(request.message);
});

// Request to extend the current selection to the "block" element containing it
function selectblock(info,tab)
{
    // chrome.extension.sendRequest({'message':'extendSelectionToBlock','data': ''},function(response){});
	chrome.tabs.sendMessage(tab.id, {selection: "extendToBlock"}, function(response) {
		// console.log(response.farewell);
	});
}

// Request to send the current selection to the server
function sendfragment(info,tab)
{
	chrome.tabs.sendMessage(tab.id, {selection: "getFragment"}, function(response) {
		response_data = response.data;
		console.log(response_data);

	    var endpoint = response_data.site_url + '/api/send_fragment/';
		delete response_data.site_url;
	    var data = JSON.stringify(response_data);
	    console.log('json data: ', data);
	    console.log('endpoint: ', endpoint);
	    var request = new XMLHttpRequest();
	    request.open("POST", endpoint);
	    request.setRequestHeader("Content-type", "application/json");
	    request.onreadystatechange = function () { 
	        if (request.readyState == 4 && request.status == 200) {
	            var json = JSON.parse(request.responseText);
	            console.log('response: ', json);
	        }
	        // else console.log('failed');
	    }
	    request.send(data);
	});
}

// Sending and receiving data in JSON format using POST method
// http://stackoverflow.com/questions/24468459/sending-a-json-to-server-and-retrieving-a-json-in-return-without-jquery
function sendblock(info,tab)
{
	url = request_data['url'];
	xpath = request_data['xpath'];
	body = request_data['body'];
	site_url = request_data['site_url'];
	console.log('url: ', url);
	console.log('xpath: ', xpath);
	console.log('body: ', body);
	console.log('site_url: ', site_url);
    // var data = JSON.stringify({ url: url, xpath: xpath });
    // var endpoint = site_url + '/api/send_block/';
    var data = JSON.stringify({ url: url, xpath: xpath, body: body });
    var endpoint = site_url + '/api/add_block/';
    console.log('json data: ', data);
    console.log('endpoint: ', endpoint);
    var request = new XMLHttpRequest();
    request.open("POST", endpoint);
    request.setRequestHeader("Content-type", "application/json");
    request.onreadystatechange = function () { 
        if (request.readyState == 4 && request.status == 200) {
            var json = JSON.parse(request.responseText);
            console.log('response: ', json);
        }
        // else console.log('failed');
    }
    request.send(data);
}

//Request to extend the current selection to the "block" element containing it
function viewblock(info,tab)
{
	chrome.tabs.sendMessage(tab.id, {selection: "findBlock"}, function(response) {
		response_data = response.data;
		console.log(response_data);

		var site_url = response_data.site_url;
		var endpoint = site_url + '/api/find_block/';
		delete response_data.site_url;
	    var data = JSON.stringify(response_data);
	    console.log('json data: ', data);
	    console.log('endpoint: ', endpoint);
	    var request = new XMLHttpRequest();
	    request.open("POST", endpoint);
	    request.setRequestHeader("Content-type", "application/json");
	    request.onreadystatechange = function () { 
	        if (request.readyState == 4 && request.status == 200) {
	            var json = JSON.parse(request.responseText);
	            console.log('response: ', json);
	            block_url = site_url + '/block/' + json['block'] + '/';
	        	chrome.tabs.sendMessage(tab.id, {selection: "viewBlock", block_url: block_url}, function(response2) {
	        		console.log(response2.data);
	        	});
	        }
	        // else console.log('failed');
	    }
	    request.send(data);
	});
}

// Chrome's context menus
// https://developer.chrome.com/extensions/contextMenus#method-create
var contexts = ["selection"];
for (var i = 0; i < contexts.length; i++)
{
    var context = contexts[i];
    chrome.contextMenus.create({"title": "Send selected fragment", "contexts":[context], "onclick": sendfragment}); 
    chrome.contextMenus.create({"title": "Extend selection to containing block", "contexts":[context], "onclick": selectblock}); 
    chrome.contextMenus.create({"title": "Send block for translation", "contexts":[context], "onclick": sendblock}); 
    chrome.contextMenus.create({"title": "View block offline", "contexts":[context], "onclick": viewblock}); 
}
