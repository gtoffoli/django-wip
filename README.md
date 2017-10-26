# django-wip

**FairVillage - Website Internationalisation Platform**

*FairVillage WIP* (WIP = Website Internationalisation Platform) is an Editorial Desk for the Internationalisation (i18n) of websites; it has been developed inside *FairVillage*, a sub-project of the *FI-Adopt* valorization project of the *FI-WARE* EU Programme.

WIP is an original application of the *Translation Proxy* concept: an approach to the translation of a web site that operates
from outside, by intercepting the request for a web page and serving to the user a page containing translated content. In the translation proxy approach, contents aren't translated at sight, as with GoogleTranslate; rather, fragments of the web page are replaced in real-time with translations that have been prepared offline and revised in context. Obviously, some caching can be applied to improve performance.

Since the background work involved in setting up a proxy site of high quality is critical, WIP aims to support it at a high extent. Learning mechanisms and knowledge reuse are exploited to make the translation and revision tasks more and more productive and to minimize the maintenance-related tasks.

On the server side, WIP integrates the Django web application framework and many Python libraries, such as [*NLTK*](https://github.com/nltk/nltk) and [*Scrapy*](https://github.com/scrapy/scrapy); it can also interface web services providing Translation Memories (TM), Machine Translation (MT) and access to large networks of linguistic resources. Currently we are experimenting also [*eflomal*](https://github.com/robertostling/eflomal), an advanced algorithm for word-level aligning of the source and the translated sentences.

On the client side, WIP builds on Javascript libraries, such as jQuery, and on plugin technologies available for FireFox and Chrome.

WIP includes a lot of algorithms and language resources that make it also an ideal tool for research and education in many language-related fields, such as text analysis, web mining, translation and language learning.

The production version of *FairVillage WIP* runs on Linux-Ubuntu, in a cloud architecture based on the [FI-Lab](https://www.fiware.org/lab/), but we are performing most of the development on Windows.

