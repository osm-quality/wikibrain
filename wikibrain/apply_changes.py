class PrerequisiteFailedError(Exception):
    pass

def apply_changes(tags, tagging_changes):
    for change in tagging_changes:
        for removed in change["from"]:
            if change["from"][removed] != None:
                if tags.get(removed) != change["from"][removed]:
                    raise PrerequisiteFailedError()
                del tags[removed]
            else:
                if removed in tags:
                    raise PrerequisiteFailedError()
        for added in change["to"]:
            if tags.get(added) != None:
                raise PrerequisiteFailedError()
            if change["to"][added] != None:
                tags[added] = change["to"][added]
    return tags
