# -*- coding: utf-8 -*-

# converted from the javascript library of the Wikimedia Content translation project
# https://github.com/wikimedia/mediawiki-services-cxserver/blob/master/bin/linearize

"""
var script, xhtmlSource, xhtml, parser,
    fs = require( 'fs' ),
    LinearDoc = require( __dirname + '/../lineardoc' );

script = process.argv[ 1 ];
if ( process.argv.length !== 3 ) {
    process.stderr.write(
        'Usage: node ' + script + ' xhtmlSource\n' +
        'xhtml must be wrapped in a block element such as <p>...</p> or <div>..</div>.\n'
    );
    process.exit( 1 );
}

xhtmlSource = process.argv[ 2 ];
xhtml = fs.readFileSync( xhtmlSource, 'utf8' );
parser = new LinearDoc.Parser();
parser.init();
parser.write( xhtml );
process.stdout.write( parser.builder.doc.dumpXml() );
"""

from wip.lineardoc.Parser import Parse

def linearize(xhtml):
    lineardoc = Parse(xhtml)
    return lineardoc.dumpXml()
