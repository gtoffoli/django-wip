# -*- coding: utf-8 -*-

from models import Site, Block

def set_blocks_language(slug, dry=False):
    from wip.utils import guess_block_language
    site = Site.objects.get(slug=slug)
    blocks = Block.objects.filter(site=site, language__isnull=True)
    for block in blocks:
        code = guess_block_language(block)
        print block.id, code
        if code in ['en',] and not dry:
            block.language_id = code
            block.save()
