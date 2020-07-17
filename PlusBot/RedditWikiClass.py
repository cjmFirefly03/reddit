from abc import ABCMeta, abstractmethod


class RedditWikiClass(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def create_from_wiki(self, row, **kwargs):
        pass

    @abstractmethod
    def get_id(self):
        pass

