// content.js

// from the settings.py module of the wip app (Django)
var BLOCK_TAGS = [
   'html', 'body', 'header', 'hgroup', 'main',  'aside', 'footer',
   'address', 'article', 'field', 'section', 'nav',
   'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'dl', 'dt', 'dd',
   'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
   'blockquote', 'pre', 'noscript',
   'img', 'figure', 'figcaption', 'canvas', 'video',
   'form', 'fieldset', 'input', 'button', 'select', 'option', 'textarea', 'output',
];

// Get the DOM element which contains the current selection
// http://stackoverflow.com/questions/1335252/how-can-i-get-the-dom-element-which-contains-the-current-selection
// function getSelectionBoundaryElement(isStart) {
function getSelectionBoundaryElement(sel, isStart) {
    var range, container;
    if (sel.getRangeAt) {
        if (sel.rangeCount > 0) {
            range = sel.getRangeAt(0);
        }
    } else {
        // Old WebKit
        range = document.createRange();
        range.setStart(sel.anchorNode, sel.anchorOffset);
        range.setEnd(sel.focusNode, sel.focusOffset);

        // Handle the case when the selection was selected backwards (from the end to the start in the document)
        if (range.collapsed !== sel.isCollapsed) {
            range.setStart(sel.focusNode, sel.focusOffset);
            range.setEnd(sel.anchorNode, sel.anchorOffset);
        }
   }

    if (range) {
       container = range[isStart ? "startContainer" : "endContainer"];

       // Check if the container is a text node and return its parent if so
       // return container.nodeType === 3 ? container.parentNode : container;
       if (container.nodeType === 3)
    	   container = container.parentNode;
       // Check if the container is not a block node and return its parent if so
       while (BLOCK_TAGS.indexOf(container.tagName.toLowerCase())<0)
    	   container = container.parentNode;
       return container;
    }   
}

// Get xpath position of an element
// http://stackoverflow.com/questions/3454526/how-to-calculate-the-xpath-position-of-an-element-using-javascript
function getXPath(element)
{
    var xpath = '';
    for ( ; element && element.nodeType == 1; element = element.parentNode )
    {
        var id = $(element.parentNode).children(element.tagName).index(element) + 1;
        id > 1 ? (id = '[' + id + ']') : (id = '');
        xpath = '/' + element.tagName.toLowerCase() + id + xpath;
    }
    return xpath;
}

// Cancel range selection
//http://stackoverflow.com/questions/3169786/clear-text-selection-with-javascript
function cancelSelection() {
	var sel = window.getSelection ? window.getSelection() : document.selection;
	if (sel) {
	    if (sel.removeAllRanges) {
	        sel.removeAllRanges();
	    } else if (sel.empty) {
	        sel.empty();
	    }
	}
}

// On down click of left mouse button cancel range selection
// http://stackoverflow.com/questions/3169786/clear-text-selection-with-javascript
document.addEventListener('mousedown', function(event)
{
    var isLeftMB = event.button==0;
    console.log(event);
    console.log(isLeftMB);

    if (isLeftMB) {
    	/* 
    	var sel = window.getSelection ? window.getSelection() : document.selection;
    	if (sel) {
    	    if (sel.removeAllRanges) {
    	        sel.removeAllRanges();
    	    } else if (sel.empty) {
    	        sel.empty();
    	    }
    	}
    	*/
    	cancelSelection();
    }
})


// Get source code fragment with range from a selection?
// http://stackoverflow.com/questions/24846993/get-source-code-fragment-with-range-from-a-selection
// http://jsfiddle.net/breWL/3/

function getHtml(node) {
    if (node.nodeName === "#text") {
        return node.textContent;
    } 
    var children =  node.childNodes;
    var html = "";
    for (var i = 0; i < children.length; i++) {
        html += getHtml(children[i]);
    }
    var innerStart = node.outerHTML.lastIndexOf(node.innerHTML);
    var innerEnd = innerStart + node.innerHTML.length;
    html = node.outerHTML.substr(0, innerStart) + html + node.outerHTML.substr(innerEnd);
    return html;
}

function getPosition(node, child, childOffset) {
    if (!node.contains(child)) {
        return -1;
    }
    var children = node.childNodes;
    var pos = 0;
    for (var i = 0; i< children.length; i++) {
        if (children[i] === child) {
            pos += childOffset;
            break;
        } else if (children[i].contains(child)) {
            pos += getPosition(children[i], child, childOffset);
            break;
        } else if (children[i].nodeName === "#text") {
            pos += children[i].textContent.length;
        } else {
            // pos += children[i].getHtml().length;
            pos += getHtml(children[i]).length;
        }
    }
    if (node.nodeName !== "#text") {
        pos += node.outerHTML.lastIndexOf(node.innerHTML);
    }
    return pos;
}

// Return an object describing the current selected fragment
function getSelectedFragment() {
    var selection = window.getSelection();
    var selected_text = selection.toString();
	var data = {
		url : window.location.href,
		site_url: window.location.protocol + "//" + window.location.host
    }

	if (selection.rangeCount === 0)
        return data;
	var range = selection.getRangeAt(0);
    var object = range.commonAncestorContainer.nodeName === "#text"? range.commonAncestorContainer.parentElement: range.commonAncestorContainer;
    var source =  getHtml(object);
    var start = getPosition(object, range.startContainer, range.startOffset);
    var end = getPosition(object, range.endContainer, range.endOffset);
    data.source = source;
    data.start = start;
    data.end = end;
    console.log(data);
    return data;
}

// Extend the range selection to the containing "block"
function extendSelectionToBlock() {
    var selection = window.getSelection();
    var selected_text = selection.toString();
    var isStart = true;

    if (selected_text.length) {
    	console.log(selected_text);
    	var element = getSelectionBoundaryElement(selection, isStart);
    	console.log(element);
    	var range = document.createRange();
    	range.setStartBefore(element);
    	range.setEndAfter(element);
    	selection.removeAllRanges();
    	selection.addRange(range);
    	var xpath = getXPath(element);
    	var body = element.outerHTML;
    	console.log(xpath);
    	console.log(body);
    	data = {
        	url : window.location.href,
    		xpath: xpath,
    		body: body,
    		site_url: window.location.protocol + "//" + window.location.host
    	}
        console.log(data);
        chrome.extension.sendRequest({'message':'sendBlock','data': data},function(response){});
    }
}

// Find selected block in the WIP server
function findBlock() {
	console.log('in findBlock')
	var data = {
		url : window.location.href,
		site_url: window.location.protocol + "//" + window.location.host
	}
    var selection = window.getSelection();
	if (selection.rangeCount === 0)
        return data;
    var isStart = true;
	var element = getSelectionBoundaryElement(selection, isStart);
	console.log(element);
	var xpath = getXPath(element);
	console.log(xpath);
	data.xpath = xpath;
    console.log(data);
	return data;
}
// View selected block offline in the WIP server
function viewBlock(block_url) {
	console.log('in viewBlock')
	window.open(block_url,'block');
	var data = { function: 'viewBlock', status: 'ok'}
	return data;
}

/*
// this handler process the mouseup event of left mouse button at the end of text selection
document.addEventListener('mouseup', function(event)
{
    var selection = window.getSelection();
    var selected_text = selection.toString();
    var isLeftMB = event.button==0;

    if (isLeftMB && selected_text.length) {
    	console.log(selected_text);
    	extendSelectionToBlock();
    }
})
*/

// The Range interface represents a fragment of a document that can contain nodes and parts of text nodes.
// https://developer.mozilla.org/en-US/docs/Web/API/Range
// Message Passing (extension.sendRequest is Deprecated since Chrome 33. Please use runtime.sendMessage)
// https://developer.chrome.com/extensions/messaging
chrome.runtime.onMessage.addListener(
	function(request, sender, sendResponse) {
		console.log(sender.tab ? "from a content script:" + sender.tab.url : "from the extension");
		if (request.selection == "extendToBlock") {
			// sendResponse({farewell: "goodbye"});
			extendSelectionToBlock();
		}
		else if (request.selection == "findBlock") {
			console.log("findBlock")
			sendResponse({ data: findBlock() });
		}
		else if (request.selection == "viewBlock") {
			console.log("viewBlock")
			sendResponse({ data: viewBlock(request.block_url) });
		}
		else if (request.selection == "getFragment") {
			sendResponse({ data: getSelectedFragment() });
		}
	}
);