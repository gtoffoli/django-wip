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
    	console.log(xpath);
    	data = {
			url : window.location.href,
    		xpath: xpath,
    		site_url: window.location.protocol + "//" + window.location.host
    	}
        chrome.extension.sendRequest({'message':'sendBlock','data': data},function(response){});
    }
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

// https://developer.chrome.com/extensions/messaging
chrome.runtime.onMessage.addListener(
	function(request, sender, sendResponse) {
		console.log(sender.tab ? "from a content script:" + sender.tab.url : "from the extension");
		if (request.selection == "extendToBlock")
			// sendResponse({farewell: "goodbye"});
			extendSelectionToBlock();
	}
);