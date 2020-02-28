class PrerequisiteFailedError(Exception):
    pass

def apply_changes(tags, tagging_changes):
    for change in tagging_changes:
        for removed in change["from"]:
            if tags.get(removed) != change["from"][removed]:
                raise PrerequisiteFailedError()
            del tags[removed]
        for added in change["to"]:
            if tags.get(added) != None:
                raise PrerequisiteFailedError()
            if change["to"][added] != None:
                tags[added] = change["to"][added]
    return tags
