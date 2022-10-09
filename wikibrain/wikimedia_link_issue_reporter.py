import wikimedia_connection
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import wikimedia_connection.wikidata_processing as wikidata_processing
import geopy.distance
import re
import yaml
from wikibrain import wikipedia_knowledge
from wikibrain import wikidata_knowledge

class ErrorReport:
    def __init__(self, error_message=None, error_general_intructions=None, desired_wikipedia_target=None, debug_log=None, error_id=None, prerequisite=None, extra_data=None, proposed_tagging_changes=None):
        # to include something in serialization - modify data function
        self.error_id = error_id
        self.error_message = error_message
        self.error_general_intructions = error_general_intructions
        self.debug_log = debug_log
        self.current_wikipedia_target = None #TODO - eliminate, start from wikipedia validator using this data
        self.desired_wikipedia_target = desired_wikipedia_target  #TODO - eliminate, start from wikipedia validator using this data
        self.prerequisite = prerequisite
        self.extra_data = extra_data # TODO - replace by more specific
        self.proposed_tagging_changes = proposed_tagging_changes
        self.osm_object_url = None
        self.location = None
        self.tags = None

    def bind_to_element(self, element):
        self.tags = element.get_tag_dictionary()
        self.current_wikipedia_target = element.get_tag_value("wikipedia") # TODO - save all tags #TODO - how to handle multiple?
        self.osm_object_url = element.get_link()
        if element.get_coords() == None:
            self.location = (None, None)
        else:
            self.location = (element.get_coords().lat, element.get_coords().lon)

    def data(self):
        return dict(
            error_id = self.error_id,
            error_message = self.error_message,
            error_general_intructions = self.error_general_intructions,
            debug_log = self.debug_log,
            osm_object_url = self.osm_object_url,
            current_wikipedia_target = self.current_wikipedia_target, #TODO - eliminate, start from wikipedia validator using this data
            desired_wikipedia_target = self.desired_wikipedia_target, #TODO - eliminate, start from wikipedia validator using this data
            proposed_tagging_changes = self.proposed_tagging_changes,
            extra_data = self.extra_data,
            prerequisite = self.prerequisite,
            location = self.location,
            tags = self.tags,
        )
    def yaml_output(self, filepath):
        with open(filepath, 'a') as outfile:
            yaml.dump([self.data()], outfile, default_flow_style=False)

class WikimediaLinkIssueDetector:
    def __init__(self, forced_refresh=False, expected_language_code=None, languages_ordered_by_preference=[], additional_debug=False, allow_requesting_edits_outside_osm=False, allow_false_positives=False):
        self.forced_refresh = forced_refresh
        self.expected_language_code = expected_language_code
        self.languages_ordered_by_preference = languages_ordered_by_preference
        self.additional_debug = additional_debug
        self.allow_requesting_edits_outside_osm = allow_requesting_edits_outside_osm
        self.allow_false_positives = allow_false_positives

    def get_problem_for_given_element(self, element):
        tags = element.get_tag_dictionary()
        object_type = element.get_element().tag
        location = (element.get_coords().lat, element.get_coords().lon)
        object_description = self.describe_osm_object(element)
        return self.get_the_most_important_problem_generic(tags, location, object_type, object_description)

    def get_problem_for_given_tags(self, tags, object_type, object_description):
        location = None
        return self.get_the_most_important_problem_generic(tags, location, object_type, object_description)

    def get_the_most_important_problem_generic(self, tags, location, object_type, object_description):
        if self.object_should_be_deleted_not_repaired(object_type, tags):
            return None
        
        something_reportable = self.use_special_properties_allowing_to_ignore_wikipedia_tags(tags)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.critical_structural_issue_report(object_type, tags)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.freely_reorderable_issue_reports(object_description, location, tags)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.add_wikipedia_and_wikidata_based_on_each_other(tags)
        if something_reportable != None:
            return something_reportable

        return None

    def use_special_properties_allowing_to_ignore_wikipedia_tags(self, tags):
        if tags.get("wikidata") != None:
            if tags.get("teryt:simc") != None:
                wikidata_simc_object = wikimedia_connection.get_property_from_wikidata(tags.get("wikidata"), 'P4046')
                if wikidata_simc_object == None:
                    return None
                wikidata_simc = wikidata_simc_object[0]['mainsnak']['datavalue']['value']
                if wikidata_simc != tags.get("teryt:simc"):
                    message = "mismatching teryt:simc codes in wikidata (" + tags.get("wikidata") + ") where " + str(wikidata_simc) + " is declared and in osm element, where teryt:simc=" + tags.get("teryt:simc") + " is declared"
                    return ErrorReport(
                                    error_id = "mismatching teryt:simc codes in wikidata and in osm element",
                                    error_message = message,
                                    prerequisite = {'wikidata': tags.get("wikidata"), "teryt:simc": tags.get("teryt:simc")},
                                    )
                wikipedia_expected = self.get_best_interwiki_link_by_id(tags.get("wikidata"))
                if tags.get("wikipedia") != wikipedia_expected:
                    if wikipedia_expected != None:
                        message = "new wikipedia tag <" + wikipedia_expected + " proposed based on matching teryt:simc codes in wikidata (" + tags.get("wikidata") + ") and in osm element, where teryt:simc=" + tags.get("teryt:simc") + " is declared"
                        return ErrorReport(
                                        error_id = "wikipedia needs to be updated based on wikidata code and teryt:simc identifier",
                                        error_message = message,
                                        prerequisite = {'wikidata': tags.get("wikidata"), "teryt:simc": tags.get("teryt:simc"), 'wikipedia': tags.get("wikipedia"), },
                                        )
                    else:
                        message = " it seems that wikipedia tag should be removed given matching teryt:simc codes in wikidata (" + tags.get("wikidata") + ") and in osm element, where teryt:simc=" + tags.get("teryt:simc") + " is declared"
                        return ErrorReport(
                                        error_id = "wikipedia tag needs to be removed based on wikidata code and teryt:simc identifier",
                                        error_message = message,
                                        prerequisite = {'wikidata': tags.get("wikidata"), "teryt:simc": tags.get("teryt:simc"), 'wikipedia': tags.get("wikipedia"), },
                                        )
        return None

    def critical_structural_issue_report(self, object_type, tags):
        #TODO - is it OK?
        #if tags.get("wikipedia").find("#") != -1:
        #    return "link to section (\"only provide links to articles which are 'about the feature'\" - http://wiki.openstreetmap.org/wiki/Key:wikipedia):"

        something_reportable = self.remove_old_style_wikipedia_tags(tags)
        if something_reportable != None:
            return something_reportable

        if tags.get("wikidata") != None:
            something_reportable = self.check_is_wikidata_link_clearly_malformed(tags.get("wikidata"))
            if something_reportable != None:
                return something_reportable

            something_reportable = self.check_is_wikidata_page_existing(tags.get("wikidata"))
            if something_reportable != None:
                return something_reportable

        if tags.get("wikipedia") != None:
            language_code = wikimedia_connection.get_language_code_from_link(tags.get("wikipedia"))
            article_name = wikimedia_connection.get_article_name_from_link(tags.get("wikipedia"))

            something_reportable = self.check_is_wikipedia_link_clearly_malformed(tags.get("wikipedia"))
            if something_reportable != None:
                return something_reportable

            something_reportable = self.check_is_wikipedia_page_existing(language_code, article_name)
            if something_reportable != None:
                return something_reportable

            # early to ensure that passing later wikidata_id of article is not going to be confusing
            if tags.get("wikidata") != None: # in case of completely missing wikidata tag it is not a critical issue and will be solved 
                                             # by add_wikipedia_and_wikidata_based_on_each_other
                something_reportable = self.check_for_wikipedia_wikidata_collision(tags.get("wikidata"), language_code, article_name)
                if something_reportable != None:
                    return something_reportable

        return None

    def add_wikipedia_and_wikidata_based_on_each_other(self, tags):
        wikidata_id = None
        if tags.get("wikipedia") != None:
            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_link(tags.get("wikipedia"))
        something_reportable = self.check_is_wikidata_tag_is_misssing(tags.get('wikipedia'), tags.get('wikidata'), wikidata_id)
        if something_reportable != None:
            return something_reportable

        old_style_wikipedia_tags = self.get_old_style_wikipedia_keys(tags)

        if tags.get("wikipedia") != None:
            return None

        if tags.get('wikidata') != None and old_style_wikipedia_tags == []:
            return self.get_wikipedia_from_wikidata_assume_no_old_style_wikipedia_tags(tags.get('wikidata'), tags)

        return None

    def get_effective_wikipedia_tag(self, tags):
        wikipedia = tags.get('wikipedia')
        if wikipedia != None:
            return wikipedia
        return self.get_best_interwiki_link_by_id(tags.get('wikidata'))

    def get_effective_wikidata_tag(self, tags):
        wikidata_id = tags.get('wikidata')
        if wikidata_id != None:
            return wikidata_id
        wikipedia = tags.get('wikipedia')
        if wikipedia != None:
            return wikimedia_connection.get_wikidata_object_id_from_link(tags.get("wikipedia"))
        return None

    def replace_prerequisites_to_match_actual_tags(self, something_reportable, tags):
        """
        hack necessary in some cases :(
        
        object may have no wikidata tag at all, but it may be calculated from wikipedia tag
        in such case report may be made about wikidata_id indicating a clear issue, such as link to a disambig page

        in such case using reprequisite with wikidata=QXXXXX is wrong as object has no such tag,
        it is necessary to replace it by an actual source

        in this case function blindly assumes that wikipedia is a good replacement

        TODO: replace this monstrous hack
        """
        if 'wikidata' in something_reportable.prerequisite:
            if 'wikidata' not in tags and 'wikipedia' in tags:
                something_reportable.prerequisite.pop('wikidata')
                something_reportable.prerequisite['wikipedia'] = tags['wikipedia']
        return something_reportable

    def freely_reorderable_issue_reports(self, object_description, location, tags):
        effective_wikipedia = self.get_effective_wikipedia_tag(tags)
        effective_wikidata_id = self.get_effective_wikidata_tag(tags)
        # Note that wikipedia may be None - maybe there is just a Wikidata entry!
        # Note that effective_wikidata_id may be None - maybe it was not created yet! 

        # IDEA links from buildings to parish are wrong - but from religious admin are OK https://www.wikidata.org/wiki/Q11808149

        something_reportable = self.get_problem_based_on_wikidata_blacklist(effective_wikidata_id, tags.get('wikidata'), effective_wikipedia)
        if something_reportable != None:
            return self.replace_prerequisites_to_match_actual_tags(something_reportable, tags)

        if tags.get("information") == "board":
            if tags.get("wikipedia") != None:
                return ErrorReport(
                    error_id = "information board with wikipedia tag, not subject:wikipedia",
                    error_message = "information board topic must be tagged with subject:wikipedia tag - not with wikipedia tag",
                    prerequisite = {'wikipedia': tags.get("wikipedia"), "information": tags.get("information")},
                    )
            if tags.get("wikidata") != None:
                return ErrorReport(
                    error_id = "information board with wikidata tag, not subject:wikidata",
                    error_message = "information board topic must be tagged with subject:wikidata tag - not with wikipedia tag",
                    prerequisite = {'wikidata': tags.get("wikidata"), "information": tags.get("information")},
                    )

        something_reportable = self.get_problem_based_on_wikidata_and_osm_element(object_description, location, effective_wikidata_id, tags)
        if something_reportable != None:
            if something_reportable.error_id == "link to a list" and "#" in tags.get("wikipedia"):
                pass
                # not actually a real error, I think
            else:
                return self.replace_prerequisites_to_match_actual_tags(something_reportable, tags)

        something_reportable = self.get_wikipedia_language_issues(object_description, tags, effective_wikipedia, effective_wikidata_id)
        if something_reportable != None:
            return something_reportable

        # TODO - check disabled
        # requires resolving https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1361617968#Tagging_ruins/remains_left_after_object
        # extra support for one more parameter required
        #something_reportable = self.check_is_object_is_existing(wikidata_id)
        #if something_reportable != None:
        #    return something_reportable

        return None

    def wikidata_connection_blacklisted_and_unfixable(self):
        print("DEPRECATED, call wikidata_knowledge.blacklisted_and_unfixable_ids")
        return wikidata_knowledge.blacklisted_and_unfixable_ids()

    def wikidata_connection_blacklist(self):
        print("DEPRECATED, call wikidata_knowledge.blacklist_of_unlinkable_entries")
        return wikidata_knowledge.blacklist_of_unlinkable_entries()

    def get_problem_based_on_wikidata_blacklist(self, wikidata_id, present_wikidata_id, link):
        if wikidata_id == None:
            wikidata_id = present_wikidata_id

        try:
            prefix = wikidata_knowledge.blacklist_of_unlinkable_entries()[wikidata_id]['prefix']
        except KeyError:
            return None

        message = ("it is a typical wrong link and it has an obvious replacement, " +
            prefix + "wikipedia/" + prefix + "wikidata should be used instead")

        return ErrorReport(
                        error_id = "blacklisted connection with known replacement",
                        error_message = message,
                        prerequisite = {'wikipedia': link, 'wikidata': present_wikidata_id},
                        extra_data = prefix
                        )

    def check_is_wikidata_page_existing(self, present_wikidata_id):
        wikidata = wikimedia_connection.get_data_from_wikidata_by_id(present_wikidata_id)
        if wikidata != None:
            return None
        link = wikimedia_connection.wikidata_url(present_wikidata_id)
        return ErrorReport(
                        error_id = "wikidata tag links to 404",
                        error_message = "wikidata tag present on element points to not existing element (" + link + ")",
                        prerequisite = {'wikidata': present_wikidata_id},
                        )

    def check_is_wikipedia_link_clearly_malformed(self, link):
        if self.is_wikipedia_tag_clearly_broken(link):
            return ErrorReport(
                            error_id = "malformed wikipedia tag",
                            error_message = "malformed wikipedia tag (" + link + ")",
                            prerequisite = {'wikipedia': link},
                            )
        else:
            return None

    def check_is_wikidata_link_clearly_malformed(self, link):
        if self.is_wikidata_tag_clearly_broken(link):
            return ErrorReport(
                            error_id = "malformed wikidata tag",
                            error_message = "malformed wikidata tag (" + link + ")",
                            prerequisite = {'wikidata': link},
                            )
        else:
            return None

    def check_is_wikidata_tag_is_misssing(self, wikipedia, present_wikidata_id, wikidata_id):
        if present_wikidata_id == None and wikidata_id != None:
            return ErrorReport(
                            error_id = "wikidata from wikipedia tag",
                            error_message = wikidata_id + " may be added as wikidata tag based on wikipedia tag",
                            prerequisite = {'wikipedia': wikipedia, 'wikidata': None}
                            )
        else:
            return None

    def check_is_wikipedia_page_existing(self, language_code, article_name):
        page_according_to_wikidata = wikimedia_connection.get_interwiki_article_name(language_code, article_name, language_code, self.forced_refresh)
        if page_according_to_wikidata != None:
            # assume that wikidata is correct to save downloading page
            return None
        page = wikimedia_connection.get_wikipedia_page(language_code, article_name, self.forced_refresh)
        if page == None:
            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
            return self.report_failed_wikipedia_page_link(language_code, article_name, wikidata_id)

    def get_best_interwiki_link_by_id(self, wikidata_id):
        all_languages = wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance()
        for potential_language_code in (self.languages_ordered_by_preference + all_languages):
            if potential_language_code != None:
                potential_article_name = wikimedia_connection.get_interwiki_article_name_by_id(wikidata_id, potential_language_code, self.forced_refresh)
                if potential_article_name != None:
                    return potential_language_code + ':' + potential_article_name
        return None

    def report_failed_wikipedia_page_link(self, language_code, article_name, wikidata_id):
        error_general_intructions = ""
        error_general_intructions += "Wikipedia article linked from OSM object using wikipedia tag is missing.\n"
        error_general_intructions += "Often article was moved without leaving redirect and wikipedia tag should be edited to point to the new one.\n"
        error_general_intructions += "Article may be deleted and no longer existing, or link was never valid. In such cases wikipedia tag should be deleted."
        proposed_new_target = self.get_best_interwiki_link_by_id(wikidata_id)
        message = ""
        if proposed_new_target != None:
            message += " wikidata tag present on element points to an existing article"
        return ErrorReport(
                    error_id = "wikipedia tag links to 404",
                    error_general_intructions = error_general_intructions,
                    error_message = message,
                    prerequisite = {'wikipedia': language_code+":"+article_name},
                    desired_wikipedia_target = proposed_new_target,
                    proposed_tagging_changes = [{"from": {"wikipedia": language_code+":"+article_name}, "to": {"wikipedia": proposed_new_target}}],
                    )

    def wikidata_data_quality_warning(self):
        return "REMEMBER TO VERIFY! WIKIDATA QUALITY MAY BE POOR!"

    def check_is_object_is_existing(self, present_wikidata_id):
        if present_wikidata_id == None:
            return None
        no_longer_existing = wikimedia_connection.get_property_from_wikidata(present_wikidata_id, 'P576')
        if no_longer_existing != None:
            error_general_intructions = "Wikidata claims that this object no longer exists. Historical, no longer existing object must not be mapped in OSM - so it means that either Wikidata is mistaken or wikipedia/wikidata tag is wrong or OSM has an outdated object." + " " + self.wikidata_data_quality_warning()
            message = ""
            return ErrorReport(
                            error_id = "no longer existing object",
                            error_general_intructions = error_general_intructions,
                            error_message = message,
                            prerequisite = {'wikidata': present_wikidata_id}
                            )

    def tag_from_wikidata(self, present_wikidata_id, wikidata_property):
        from_wikidata = wikimedia_connection.get_property_from_wikidata(present_wikidata_id, wikidata_property)
        if from_wikidata == None:
            return None
        returned = wikidata_processing.decapsulate_wikidata_value(from_wikidata)
        if not isinstance(returned, str):
            print(present_wikidata_id + " unexpectedly failed within decapsulate_wikidata_value for property " + wikidata_property)
            return None
        return returned

    def generate_error_report_for_tag_from_wikidata(self, from_wikidata, present_wikidata_id, osm_key, element, id_suffix="", message_suffix = ""):
        if element.get_tag_value(osm_key) == None:
                return ErrorReport(
                            error_id = "tag may be added based on wikidata" + id_suffix,
                            error_message = str(from_wikidata) + " may be added as " + osm_key + " tag based on wikidata entry" + message_suffix + " " + self.wikidata_data_quality_warning(),
                            prerequisite = {'wikidata': present_wikidata_id, osm_key: None}
                            )
        elif element.get_tag_value(osm_key) != from_wikidata:
                if not self.allow_requesting_edits_outside_osm:
                    # typically Wikidata is wrong, not OSM
                    return None
                message = str(from_wikidata) + " conflicts with " + element.get_tag_value(osm_key) + " for " + osm_key + " tag based on wikidata entry - note that OSM value may be OK and Wikidata entry is wrong, in that case one may either ignore this error or fix Wikidata entry" + message_suffix + " " + self.wikidata_data_quality_warning()
                return ErrorReport(
                            error_id = "tag conflict with wikidata value" + id_suffix,
                            error_message = message,
                            prerequisite = {'wikidata': present_wikidata_id, osm_key: element.get_tag_value(osm_key)}
                            )

    def get_old_style_wikipedia_keys(self, tags):
        old_style_wikipedia_tags = []
        for key in tags.keys():
            if key.find("wikipedia:") != -1:
                old_style_wikipedia_tags.append(key)
        return old_style_wikipedia_tags

    def remove_old_style_wikipedia_tags(self, tags):
        old_style_wikipedia_tags = self.get_old_style_wikipedia_keys(tags)

        reportable = self.check_is_invalid_old_style_wikipedia_tag_present(old_style_wikipedia_tags, tags)
        if reportable:
            return reportable

        if old_style_wikipedia_tags != []:
            return self.convert_old_style_wikipedia_tags(old_style_wikipedia_tags, tags)
        return None

    def check_is_invalid_old_style_wikipedia_tag_present(self, old_style_wikipedia_tags, tags):
        for key in old_style_wikipedia_tags:
            if not self.check_is_it_valid_key_for_old_style_wikipedia_tag(key):
                return ErrorReport(
                    error_id = "invalid old-style wikipedia tag",
                    error_message = "wikipedia tag in outdated form (" + key + "), is not using any known language code",
                    prerequisite = {key: tags[key]},
                    )
        return None

    def check_is_it_valid_key_for_old_style_wikipedia_tag(self, key):
        for lang in wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance():
            if "wikipedia:" + lang == key:
                return True
        return False

    def normalized_id_with_conflicts_list(self, links, wikidata_id):
        normalized_link_form = wikidata_id #may be None
        conflict_list = []
        for link in links:
            if link == None:
                conflict_list.append("one of links has value None")
            else:
                id_from_link = wikimedia_connection.get_wikidata_object_id_from_link(link, self.forced_refresh)

                if normalized_link_form == None and id_from_link != None:
                    normalized_link_form = id_from_link
                    continue
                if normalized_link_form == id_from_link and id_from_link != None:
                    continue

                language_code = wikimedia_connection.get_language_code_from_link(link)
                article_name = wikimedia_connection.get_article_name_from_link(link)
                try:
                    title_after_possible_redirects = self.get_article_name_after_redirect(language_code, article_name)
                    is_article_redirected = (article_name != title_after_possible_redirects and article_name.find("#") == -1)
                    if is_article_redirected:
                        id_from_link = wikimedia_connection.get_wikidata_object_id_from_article(language_code, title_after_possible_redirects, self.forced_refresh)
                except wikimedia_connection.TitleViolatesKnownLimits:
                    pass # redirected link is invalied and not reported as noexsiting - typically due to "feature" of special handling invalid ling with lang: prefixes 
                         # for example asking about en:name article on Polish-language will return info whethere "name" article exists on enwiki!
                         # as result special check and throwing this exception is done on invalid ones
                         # and in case of link leading nowhere nothing special needs to be done and it can be silently swallowed

                if normalized_link_form == None and id_from_link != None:
                    normalized_link_form = id_from_link
                    continue
                if normalized_link_form == id_from_link and id_from_link != None:
                    continue

                text_link_description = None
                if id_from_link == None:
                    text_link_description = "no link"
                else:
                    text_link_description = "link " + id_from_link
                conflict_list.append(link + " gives " + text_link_description + " conflicting with another link " + str(normalized_link_form))
        return normalized_link_form, conflict_list

    def convert_old_style_wikipedia_tags(self, wikipedia_type_keys, tags):
        links = self.wikipedia_candidates_based_on_old_style_wikipedia_keys(tags, wikipedia_type_keys)

        if tags.get('wikipedia') != None:
            links.append(tags.get('wikipedia'))

        prerequisite = {}
        prerequisite['wikidata'] = tags.get('wikidata')
        prerequisite['wikipedia'] = tags.get('wikipedia')
        for key in wikipedia_type_keys:
            prerequisite[key] = tags.get(key)

        normalized, conflicts = self.normalized_id_with_conflicts_list(links, tags.get('wikidata'))
        if conflicts != []:
            return ErrorReport(
                error_id = "wikipedia tag in outdated form and there is mismatch between links",
                error_message = "wikipedia tag in outdated form (" + str(wikipedia_type_keys) + ", with following conflicts: " + str(conflicts) + "). Mismatch between different links happened and requires human judgment to solve.",
                prerequisite = prerequisite,
                )
        elif tags.get('wikipedia') == None:
            new_wikipedia = self.get_best_interwiki_link_by_id(normalized)
            return ErrorReport(
                error_id = "wikipedia tag from wikipedia tag in an outdated form",
                error_message = "wikipedia tag in outdated form (" + str(wikipedia_type_keys) + "), wikipedia tag may be added",
                prerequisite = prerequisite,
                desired_wikipedia_target = new_wikipedia,
                proposed_tagging_changes = [{"from": {"wikipedia": None}, "to": {"wikipedia": new_wikipedia}}],
                )
        else:
            from_tags = {}
            for key in wikipedia_type_keys:
                from_tags[key] = tags.get(key)
            return ErrorReport(
                error_id = "wikipedia tag in an outdated form for removal",
                error_message = "wikipedia tag in outdated form (" + str(wikipedia_type_keys) + "), with wikipedia and wikidata tag present and may be safely removed",
                prerequisite = prerequisite,
                proposed_tagging_changes = [{"from": from_tags, "to": {}}],
                )

    def get_wikipedia_from_wikidata_assume_no_old_style_wikipedia_tags(self, present_wikidata_id, tags):
        location = (None, None)
        description = "object with wikidata=" + present_wikidata_id
        problem_indicated_by_wikidata = self.get_problem_based_on_wikidata(present_wikidata_id, tags, description, location)
        if problem_indicated_by_wikidata:
            return problem_indicated_by_wikidata

        link = self.get_best_interwiki_link_by_id(present_wikidata_id)
        if link == None:
            return None
        language_code = wikimedia_connection.get_language_code_from_link(link)
        if language_code in ["ceb"]:
            return None # not a real Wikipedia
        elif language_code == self.expected_language_code:
            return ErrorReport(
                error_id = "wikipedia from wikidata tag",
                error_message = "without wikipedia tag, without wikipedia:language tags, with wikidata tag present that provides article, article language is not surprising",
                desired_wikipedia_target = link,
                prerequisite = {'wikipedia': None, 'wikidata': present_wikidata_id},
                proposed_tagging_changes = [{"from": {"wikipedia": None}, "to": {"wikipedia": link}}],
                )
        else:
            return ErrorReport(
                error_id = "wikipedia from wikidata tag, unexpected language",
                error_message = "without wikipedia tag, without wikipedia:language tags, with wikidata tag present that provides article",
                desired_wikipedia_target = link,
                prerequisite = {'wikipedia': None, 'wikidata': present_wikidata_id},
                proposed_tagging_changes = [{"from": {"wikipedia": None}, "to": {"wikipedia": link}}],
                )

    def wikipedia_candidates_based_on_old_style_wikipedia_keys(self, tags, wikipedia_type_keys):
        links = []
        for key in wikipedia_type_keys:
            language_code = wikimedia_connection.get_text_after_first_colon(key) # wikipedia:pl -> pl
            article_name = tags.get(key)
            article_link_from_old_style_tag = language_code + ":" + article_name
            if ":" in article_name:
                potential_already_present_prefix_length = len(language_code) + 1
                if language_code + ":" == article_name[:potential_already_present_prefix_length]:
                    # cases like https://www.openstreetmap.org/node/1735170302
                    # wikipedia:de = de:Troszyn (Mieszkowice)
                    # note double de
                    article_link_from_old_style_tag = article_name
                    language_code = wikimedia_connection.get_text_before_first_colon(article_name)
                    article_name = wikimedia_connection.get_text_after_first_colon(article_name)

            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
            if wikidata_id == None:
                links.append(article_link_from_old_style_tag)
                continue

            link = self.get_best_interwiki_link_by_id(wikidata_id)
            if link == None:
                links.append(article_link_from_old_style_tag)
                continue

            links.append(link)
        return list(set(links))

    def get_wikidata_id_after_redirect(self, wikidata_id):
        wikidata_data = wikimedia_connection.get_data_from_wikidata_by_id(wikidata_id)
        try:
            return wikidata_data['entities'][wikidata_id]['id']
        except KeyError as e:
            print(e)
            print("requested <" + str(wikidata_id) + ">)")
            print(wikidata_data)
            raise e

    def get_article_name_after_redirect(self, language_code, article_name):
        try:
            return wikimedia_connection.get_from_wikipedia_api(language_code, "", article_name)['title']
        except KeyError as e:
            print(e)
            print("requested <" + str(language_code) + ", <" + str(article_name) + ">)")
            raise e

    def check_for_wikipedia_wikidata_collision(self, present_wikidata_id, language_code, article_name):
        if present_wikidata_id == None:
            return None

        article_name_with_section_stripped = article_name
        if article_name.find("#") != -1:
            article_name_with_section_stripped = re.match('([^#]*)#(.*)', article_name).group(1)

        wikidata_id_from_article = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name_with_section_stripped, self.forced_refresh)
        if present_wikidata_id == wikidata_id_from_article:
            return None

        base_message = "wikidata and wikipedia tags link to a different objects"
        common_message = base_message + ", because wikidata tag points to a redirect that should be followed"
        message = self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article)
        maybe_redirected_wikidata_id = self.get_wikidata_id_after_redirect(present_wikidata_id)
        if maybe_redirected_wikidata_id != present_wikidata_id:
            if maybe_redirected_wikidata_id == wikidata_id_from_article:
                return ErrorReport(
                    error_id = "wikipedia wikidata mismatch - follow wikidata redirect",
                    error_general_intructions = common_message,
                    error_message = message,
                    prerequisite = {'wikidata': present_wikidata_id, 'wikipedia': language_code+":"+article_name},
                    )

        title_after_possible_redirects = article_name
        try:
            title_after_possible_redirects = self.get_article_name_after_redirect(language_code, article_name)
        except wikimedia_connection.TitleViolatesKnownLimits:
            print("request for redirect target of <" + str(language_code) + "><" + str(article_name) + "> rejected as title was invalid")
            print("hopefully it is caught elsewhere that title is invalid")
            print("reconstructing wikipedia tag and reporting error")
            return ErrorReport(
                            error_id = "malformed wikipedia tag",
                            error_message = "malformed wikipedia tag (" + language_code + ":" + article_name + ")",
                            prerequisite = {'wikipedia': language_code + ":" + article_name },
                            )

        is_article_redirected = (article_name != title_after_possible_redirects and article_name.find("#") == -1)
        if is_article_redirected:
            wikidata_id_from_redirect = wikimedia_connection.get_wikidata_object_id_from_article(language_code, title_after_possible_redirects, self.forced_refresh)
            if present_wikidata_id == wikidata_id_from_redirect:
                common_message = base_message + ", because wikipedia tag points to a redirect that should be followed"
                message = self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article)
                message += " article redirects from " + language_code + ":" + article_name + " to " + language_code + ":" + title_after_possible_redirects
                new_wikipedia_link = language_code+":"+title_after_possible_redirects
                return ErrorReport(
                    error_id = "wikipedia wikidata mismatch - follow wikipedia redirect",
                    error_general_intructions = common_message,
                    error_message = message,
                    desired_wikipedia_target = new_wikipedia_link,
                    prerequisite = {'wikidata': present_wikidata_id, 'wikipedia': language_code+":"+article_name},
                    proposed_tagging_changes = [{"from": {"wikipedia": language_code+":"+article_name}, "to": {"wikipedia": new_wikipedia_link}}],
                    )
        message = (base_message + " (" +
                   self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article) +
                   " wikidata id assigned to linked Wikipedia article)")
        if maybe_redirected_wikidata_id != present_wikidata_id:
            message += " Note that this OSM object has wikidata tag links a redirect ("
            message += present_wikidata_id  + " to " + maybe_redirected_wikidata_id + ")."
        if is_article_redirected:
            message += " Note that this OSM object has wikipedia tag that links redirect ('"
            message += article_name  + "' to '" + title_after_possible_redirects + "')."
        return ErrorReport(
            error_id = "wikipedia wikidata mismatch",
            error_message = message,
            prerequisite = {'wikidata': present_wikidata_id, 'wikipedia': language_code + ":" + article_name},
            )

    def compare_wikidata_ids(self, id1, id2):
        if id1 == None:
            id1 = "(missing)"
        if id2 == None:
            id2 = "(missing)"
        return id1 + " vs " + id2

    def is_wikipedia_tag_clearly_broken(self, link):
        language_code = wikimedia_connection.get_language_code_from_link(link)
        if self.is_language_code_clearly_broken(language_code):
            return True
        article_name = wikimedia_connection.get_article_name_from_link(link)
        if self.is_article_name_clearly_broken(article_name):
            return True
        return False

    def is_wikidata_tag_clearly_broken(self, link):
        if link == None:
            return True
        if len(link) < 2:
            return True
        if link[0] != "Q":
            return True
        if re.search(r"^\d+\Z",link[1:]) == None:
            return True
        return False

    def is_article_name_clearly_broken(self, link):
        # TODO - implement other indicators from https://en.wikipedia.org/wiki/Wikipedia:Naming_conventions_(technical_restrictions)
        language_code = wikimedia_connection.get_language_code_from_link(link)

        # https://en.wikipedia.org/wiki/Wikipedia:Naming_conventions_(technical_restrictions)#Colons
        if language_code != None:
            if language_code in wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance():
                return True
        return False


    def is_language_code_clearly_broken(self, language_code):
        # detects missing language code
        #         unusually long language code
        #         broken language code "pl|"
        if language_code is None:
            return True
        if language_code.__len__() > 3:
            return True
        if re.search("^[a-z]+\Z",language_code) == None:
            return True
        if language_code not in wikipedia_knowledge.WikipediaKnowledge.all_wikipedia_language_codes_order_by_importance():
            return True
        return False

    def get_wikipedia_language_issues(self, object_description, tags, wikipedia, wikidata_id):
        # complains when Wikipedia page is not in the preferred language,
        # in cases when it is possible
        if wikipedia == None:
            return # there may be just a Wikidata entry, without a Wikipedia article
        article_name = wikimedia_connection.get_article_name_from_link(wikipedia)
        language_code = wikimedia_connection.get_language_code_from_link(wikipedia)
        if self.expected_language_code is None:
            return None
        if self.expected_language_code == language_code:
            return None
        prerequisite = {'wikipedia': language_code+":"+article_name}
        reason = self.why_object_is_allowed_to_have_foreign_language_label(object_description, wikidata_id)
        if reason != None:
            if self.additional_debug:
                print(object_description + " is allowed to have foreign wikipedia link, because " + reason)
            return None
        correct_article = wikimedia_connection.get_interwiki_article_name(language_code, article_name, self.expected_language_code, self.forced_refresh)
        if correct_article != None:
            error_message = "wikipedia page in unexpected language - " + self.expected_language_code + " was expected:"
            good_link = self.expected_language_code + ":" + correct_article
            return ErrorReport(
                error_id = "wikipedia tag unexpected language",
                error_message = error_message,
                desired_wikipedia_target = good_link,
                proposed_tagging_changes = [{"from": {"wikipedia": language_code+":"+article_name}, "to": {"wikipedia": good_link}}],
                prerequisite = prerequisite,
                )
        else:
            if not self.allow_requesting_edits_outside_osm:
                return None
            if not self.allow_false_positives:
                return None
            error_message = "wikipedia page in unexpected language - " + self.expected_language_code + " was expected, no page in that language was found:"
            return ErrorReport(
                error_id = "wikipedia tag unexpected language, article missing",
                error_message = error_message,
                prerequisite = prerequisite,
                )
        assert(False)

    def should_use_subject_message(self, type, special_prefix, wikidata_id):
        link = self.get_best_interwiki_link_by_id(wikidata_id)
        linked_object = "wikidata entry (" + wikidata_id + ")"
        if link != None:
            article_name = wikimedia_connection.get_article_name_from_link(link)

        special_prefix_text = ""
        if special_prefix != None:
            special_prefix_text = "or " + special_prefix + "wikipedia"
        message = "linked " + linked_object + " is about """ + type + \
        ", so it is very unlikely to be correct \n\
        subject:wikipedia=* " + special_prefix_text + " tag would be probably better \
        (see https://wiki.openstreetmap.org/wiki/Key:wikipedia#Secondary_Wikipedia_links for full list of what else may be applicable) \n\
        in case of change remember to remove wikidata tag if it is present \n\
        object categorised by Wikidata - wrong classification may be caused by wrong data on Wikidata"
        return message

    def get_should_use_subject_error(self, type, special_prefix, wikidata_id):
        return ErrorReport(
            error_id = "should use a secondary wikipedia tag - linking to " + type,
            error_message = self.should_use_subject_message(type, special_prefix, wikidata_id),
            prerequisite = {'wikidata': wikidata_id},
            )

    def get_list_of_links_from_disambig(self, wikidata_id):
        link = self.get_best_interwiki_link_by_id(wikidata_id)
        if link == None:
            print("ops, no language code matched for " + wikidata_id)
            return []
        article_name = wikimedia_connection.get_article_name_from_link(link)
        language_code = wikimedia_connection.get_language_code_from_link(link)
        links_from_disambig_page = wikimedia_connection.get_from_wikipedia_api(language_code, "&prop=links", article_name)['links']
        returned = []
        for link in links_from_disambig_page:
            if link['ns'] == 0:
                returned.append({'title': link['title'], 'language_code': language_code})
        return returned

    def distance_in_km_to_string(self, distance_in_km):
        if distance_in_km > 3:
            return str(int(distance_in_km)) + " km"
        else:
            return str(int(distance_in_km*1000)) + " m"

    def distance_in_km_of_wikidata_object_from_location(self, coords_given, wikidata_id):
        if wikidata_id == None:
            return None
        location_from_wikidata = wikimedia_connection.get_location_from_wikidata(wikidata_id)
        # recommended by https://stackoverflow.com/a/43211266/4130619
        # documentation on https://github.com/geopy/geopy#measuring-distance
        # geopy.distance.distance((latititude, longitude), (latititude, longitude))
        return geopy.distance.distance(coords_given, location_from_wikidata).km

    def get_distance_description_between_location_and_wikidata_id(self, location, wikidata_id):
        if location == (None, None):
            return " <no location data>"
        distance = self.distance_in_km_of_wikidata_object_from_location(location, wikidata_id)
        if distance == None:
            return " <no location data on wikidata>"
        return ' is ' + self.distance_in_km_to_string(distance) + " away"

    def get_list_of_disambig_fixes(self, location, element_wikidata_id):
        #TODO open all pages, merge duplicates using wikidata and list them as currently
        returned = ""
        links = self.get_list_of_links_from_disambig(element_wikidata_id)
        if element_wikidata_id == None:
            return "page without wikidata element, unable to load link data. Please, create wikidata element (TODO: explain how it can be done)"
        if links == None:
            return "TODO improve language handling on foreign disambigs"
        for link in links:
            link_wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(link['language_code'], link['title'])
            distance_description = self.get_distance_description_between_location_and_wikidata_id(location, link_wikidata_id)
            returned += link['title'] + distance_description + "\n"
        return returned

    def get_error_report_if_secondary_wikipedia_tag_should_be_used(self, effective_wikidata_id, tags):
        # contains ideas based partially on constraints in https://www.wikidata.org/wiki/Property:P625
        class_error = self.get_error_report_if_type_unlinkable_as_primary(effective_wikidata_id, tags)
        if class_error != None:
            return class_error

        property_error = self.get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary(effective_wikidata_id)
        if property_error != None:
            return property_error

    def get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary(self, wikidata_id):
        if wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P247') != None:
            return self.get_should_use_subject_error('a spacecraft', 'name:', wikidata_id)
        if wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P279') != None:
            return self.get_should_use_subject_error('an uncoordinable generic object', 'name:', wikidata_id) 

    def get_error_report_if_type_unlinkable_as_primary(self, effective_wikidata_id, tags):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(effective_wikidata_id, self.ignored_entries_in_wikidata_ontology()):
            potential_failure = self.get_reason_why_type_makes_object_invalid_primary_link(type_id)
            if potential_failure != None:
                if potential_failure['what'] == "a human" and tags.get('boundary') == 'aboriginal_lands':
                    pass # cases like https://www.openstreetmap.org/way/758139284 where Wikipedia article bundles ethicity group and reservation land in one article
                else:
                    return self.get_should_use_subject_error(potential_failure['what'], potential_failure['replacement'], effective_wikidata_id)
        return None

    def get_reason_why_type_makes_object_invalid_primary_link(self, type_id):
        # TODO - also generate_webpage file must be updated
        if type_id == 'Q5':
            return {'what': 'a human', 'replacement': 'name:'}
        if type_id in ['Q18786396', 'Q16521', 'Q55983715', 'Q12045585', 'Q729', 'Q5113', 'Q38829', 'Q55983715']:
            return {'what': 'an animal or plant', 'replacement': None}
        #valid for example for museums, parishes
        #if type_id == 'Q43229':
        #    return {'what': 'an organization', 'replacement': None}
        if type_id == 'Q1344':
            return {'what': 'an opera', 'replacement': None}
        if type_id == 'Q35127':
            return {'what': 'a website', 'replacement': None}
        if type_id == 'Q17320256':
            return {'what': 'a physical process', 'replacement': None}
        if type_id == 'Q1656682' or type_id == 'Q4026292' or type_id == 'Q3249551' or type_id == 'Q1190554':
            return {'what': 'an event', 'replacement': None}
        if type_id == 'Q5398426':
            return {'what': 'a television series', 'replacement': None}
        if type_id == 'Q3026787':
            return {'what': 'a saying', 'replacement': None}
        if type_id == 'Q18534542':
            return {'what': 'a restaurant chain', 'replacement': 'brand:'}
        #some local banks may fit - see https://www.openstreetmap.org/node/2598972915
        #if type_id == 'Q22687':
        #    return {'what': 'a bank', 'replacement': 'brand:'}
        if type_id == 'Q507619':
            return {'what': 'a chain store', 'replacement': 'brand:'}
        # appears in constraints of coordinate property in Wikidata but not applicable to OSM
        # pl:ArcelorMittal Poland Oddział w Krakowie may be linked
        #if type_id == 'Q4830453':
        #    return {'what': 'a business enterprise', 'replacement': 'brand:'}
        if type_id == 'Q202444':
            return {'what': 'a given name', 'replacement': 'name:'}
        if type_id in ['Q29048322', 'Q22999537', 'Q16335899', 'Q1875621', 'Q2000908']:
            return {'what': 'a vehicle model or class', 'replacement': 'vehicle_type:'}
        if type_id == 'Q21502408':
            return {'what': 'a wikidata mandatory constraint', 'replacement': None}
        if type_id == 'Q14659':
            return {'what': 'a coat of arms', 'replacement': 'subject:'}
        if type_id == 'Q7048977':
            return {'what': 'an object that exists outside physical reality', 'replacement': 'subject:'}
        return None

    def get_error_report_if_wikipedia_target_is_of_unusable_type(self, location, wikidata_id):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id, self.ignored_entries_in_wikidata_ontology()):
            if type_id == 'Q4167410':
                # TODO note that pageprops may be a better source that should be used
                # it does not require wikidata entry
                # wikidata entry may be wrong
                # https://pl.wikipedia.org/w/api.php?action=query&format=json&prop=pageprops&redirects=&titles=Java%20(ujednoznacznienie)
                list = self.get_list_of_disambig_fixes(location, wikidata_id)
                error_message = "link leads to a disambig page - not a proper wikipedia link (according to Wikidata - if target is not a disambig check Wikidata entry whether it is correct)\n\n" + list
                return ErrorReport(
                    error_id = "link to an unlinkable article",
                    error_message = error_message,
                    prerequisite = {'wikidata': wikidata_id},
                    )
            if type_id == 'Q13406463':
                error_message = "article linked in wikipedia tag is a list, so it is very unlikely to be correct"
                return ErrorReport(
                    error_id = "link to a list",
                    error_message = error_message,
                    prerequisite = {'wikidata': wikidata_id},
                    )
            if type_id == 'Q20136634':
                error_message = "article linked in wikipedia tag is an overview article, so it is very unlikely to be correct"
                return ErrorReport(
                    error_id = "link to an unlinkable article",
                    error_message = error_message,
                    prerequisite = {'wikidata': wikidata_id},
                    )

    def get_problem_based_on_wikidata_and_osm_element(self, object_description, location, effective_wikidata_id, tags):
        if effective_wikidata_id == None:
            # instance data not present in wikidata
            # not fixable easily as imports from OSM to Wikidata are against rules
            # as OSM data is protected by ODBL, and Wikidata is on CC0 license
            # also, this problem is easy to find on Wikidata itself so it is not useful to report it
            return None

        return self.get_problem_based_on_wikidata(effective_wikidata_id, tags, object_description, location)

    def get_problem_based_on_wikidata(self, effective_wikidata_id, tags, description, location):
        return self.get_problem_based_on_base_types(effective_wikidata_id, tags, description, location)

    def get_problem_based_on_base_types(self, effective_wikidata_id, tags, description, location):
        base_type_ids = wikidata_processing.get_wikidata_type_ids_of_entry(effective_wikidata_id)
        if base_type_ids == None:
            return None

        base_type_problem = self.get_problem_based_on_wikidata_base_types(location, effective_wikidata_id, tags)
        if base_type_problem != None:
            return base_type_problem

        if self.additional_debug:
            # TODO, IDEA - run with this parameter enable to start catching more issues
            # for Wikidata lovers
            self.complain_in_stdout_if_wikidata_entry_not_of_known_safe_type(effective_wikidata_id, description)


    def get_problem_based_on_wikidata_base_types(self, location, effective_wikidata_id, tags):
        unusable_wikipedia_article = self.get_error_report_if_wikipedia_target_is_of_unusable_type(location, effective_wikidata_id)
        if unusable_wikipedia_article != None:
            return unusable_wikipedia_article

        secondary_tag_error = self.get_error_report_if_secondary_wikipedia_tag_should_be_used(effective_wikidata_id, tags)
        if secondary_tag_error != None:
            return secondary_tag_error

        if location != None:
            secondary_tag_error = self.headquaters_location_indicate_invalid_connection(location, effective_wikidata_id)
            if secondary_tag_error != None:
                return secondary_tag_error

    def get_location_of_this_headquaters(self, headquarters):
        try:
            position = headquarters['qualifiers']['P625'][0]['datavalue']['value']
            position = (position['latitude'], position['longitude'])
            return position
        except KeyError:
            pass
        try:
            id_of_location = headquarters['mainsnak']['datavalue']['value']['id']
            return wikimedia_connection.get_location_from_wikidata(id_of_location)
        except KeyError:
            pass
        return (None, None)
    
    def headquaters_location_indicate_invalid_connection(self, location, wikidata_id):
        if location == (None, None):
            return None
        headquarters_location_data = wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P159')
        area_of_object = wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P2046')
        if area_of_object != None:
            return None # for example administrative boundaries such as https://www.wikidata.org/wiki/Q1364786
        if headquarters_location_data == None:
            return None
        for option in headquarters_location_data:
            location_from_wikidata = self.get_location_of_this_headquaters(option)
            if location_from_wikidata != (None, None):
                if geopy.distance.geodesic(location, location_from_wikidata).km > 20:
                    return self.get_should_use_subject_error('a company that has multiple locations', 'brand:', wikidata_id)

        return None

    def complain_in_stdout_if_wikidata_entry_not_of_known_safe_type(self, wikidata_id, description_of_source):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id, self.ignored_entries_in_wikidata_ontology()):
            if self.is_wikidata_type_id_recognised_as_OK(type_id):
                return None
        self.dump_base_types_of_object_in_stdout(wikidata_id, description_of_source)

    def output_debug_about_wikidata_item(self, wikidata_id):
        print("**********************")
        print(wikidata_processing.get_wikidata_type_ids_of_entry(wikidata_id))
        print(wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id, self.ignored_entries_in_wikidata_ontology()))
        self.complain_in_stdout_if_wikidata_entry_not_of_known_safe_type(wikidata_id, "tests")
        self.dump_base_types_of_object_in_stdout(wikidata_id, "tests")

    def dump_base_types_of_object_in_stdout(self, wikidata_id, description_of_source):
        print("----------------")
        print("https://www.wikidata.org/wiki/" + wikidata_id)
        types = wikidata_processing.get_wikidata_type_ids_of_entry(wikidata_id)
        if types == None:
            print("this entry has no types")
            return

        any_banned = False
        # if any values is banned and we need debug info, then
        # assuming that only info about banned entries needs to be provided
        # likely makes sense
        for type_id in types:
            found = wikidata_processing.get_recursive_all_subclass_of_with_depth_data(type_id, self.ignored_entries_in_wikidata_ontology())
            for entry in found:
                ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(entry["id"])
                if ban_reason != None:
                    any_banned = True
        for type_id in types:
            print("------")
            print(description_of_source)
            print("type " + "https://www.wikidata.org/wiki/" + type_id)
            self.describe_unexpected_wikidata_type(wikidata_id, type_id, show_only_banned=any_banned)

    def callback_reporting_banned_categories(self, category_id):
        ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(category_id)
        if ban_reason != None:
            return " banned as it is " + ban_reason['what'] + " !!!!!!!!!!!!!!!!!!!!!!!!!!"
        return ""

    @staticmethod
    def ignored_entries_in_wikidata_ontology():
        too_abstract_or_wikidata_bugs = wikidata_processing.wikidata_entries_for_abstract_or_very_broad_concepts()

        # https://www.wikidata.org/wiki/Talk:Q41554881#Problematic_description_and_classification
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1528309435#Geysers_are_classified_as_events._What_exactly_went_wrong?
        too_abstract_or_wikidata_bugs.append("Q41554881")

        # religious art mess
        # maybe it can be resolved, see following
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1361617968#How_to_prevent_Maria_column_from_being_classified_as_a_process?
        too_abstract_or_wikidata_bugs.append('Q2864737')

        too_abstract_or_wikidata_bugs.append('Q47848') # concrete objects are marked as subclass of 
        # sacred architecture (architectural practices used in places of worship) [https://www.wikidata.org/wiki/Q47848]
        # as result I need to skip it, see for example https://www.wikidata.org/wiki/Q775129
        too_abstract_or_wikidata_bugs.append('Q2860334') # exactly the same ("church architecture")

        too_abstract_or_wikidata_bugs.append('Q1263068') # duplicate database entry - self-report of Wikidata ontology bug
        too_abstract_or_wikidata_bugs.append('Q17362920') # Wikimedia duplicated page - self-report of Wikidata ontology bug

        # trademark is ignored as even hamlet can be trademarked
        # so it provides no extra info and detangling architecture here is too tricky
        # see https://www.wikidata.org/wiki/Q1392479
        too_abstract_or_wikidata_bugs.append("Q167270")

        # "under contruction" marker, caused some pages to be listed as invalid - not going to investigate this Wikidata bug
        too_abstract_or_wikidata_bugs.append("Q12377751")

        # "Wikimedia duplicated page" - ignoring this helps to ignore Cebuano bot wiki
        # such as at https://www.wikidata.org/w/index.php?title=Q1144105&oldid=1307322140
        too_abstract_or_wikidata_bugs.append('Q17362920')

        # "Commons gallery" - it detects Wikidata mistakes for no benefit. Ignoring it silently is preferable 
        too_abstract_or_wikidata_bugs.append('Q21167233')

        # invalid value but kept with troll qualifier
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1676962494#canal_classified_as_%22non-physical_entity%22
        # https://www.wikidata.org/w/index.php?title=Wikidata:Requests_for_deletions&diff=1676964568&oldid=1676908466
        too_abstract_or_wikidata_bugs.append('Q1826691')

        # proposed road https://www.wikidata.org/wiki/Q30106829
        # skipping this as sadly some proposed roads are actually mapped in OSM :(
        # and in this case there is no agreement to delete them :(
        too_abstract_or_wikidata_bugs.append('Q30106829')
       
        return too_abstract_or_wikidata_bugs

    def describe_unexpected_wikidata_type(self, object_id_where_it_is_present, type_id, show_only_banned):
        # print entire inheritance set
        show_debug = True
        callback = self.callback_reporting_banned_categories

        found = wikidata_processing.get_recursive_all_subclass_of_with_depth_data(type_id, self.ignored_entries_in_wikidata_ontology())

        to_show = ""
        if show_only_banned:
            for index, entry in enumerate(found):
                category_id = entry["id"]
                depth = entry["depth"]
                if self.new_banned_entry_in_this_branch(found, index):
                    note = self.callback_reporting_banned_categories(category_id)
                    print(":"*depth + wikidata_processing.wikidata_description(category_id) + note)
                    
                    #print(":"*depth + "{{Q|" + category_id + "}}")

                    to_show += ":"*depth + "{{Q|" + category_id + "}}" + "\n"
                    ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(category_id)
                    if ban_reason != None:
                        header = "=== {{Q|" + object_id_where_it_is_present + "}} classified as " + ban_reason['what'] + " ===\n"
                        with open("wikidata_report.txt", "a") as myfile:
                            myfile.write(header + to_show + "\n\n")
        else:
            parent_categories = wikidata_processing.get_recursive_all_subclass_of(type_id, self.ignored_entries_in_wikidata_ontology(), show_debug, callback)
            #for parent_category in parent_categories:
            #    print("if type_id == '" + parent_category + "':")
            #    print(wikidata_processing.wikidata_description(parent_category))

    def new_banned_entry_in_this_branch(self, data, checked_position):
        #print("00000000000000000000000000")
        #print(self.get_reason_why_type_makes_object_invalid_primary_link("Q7048977"))
        #print(checked_position, data[checked_position])
        index = checked_position - 1
        relevant_level = data[checked_position]["depth"] - 1
        # higher depth is not relevant as it is some other branch with a sgared parent
        # it can be only lower than 1 - as depth increases by one
        while index > 0:
            if data[index]["depth"] == relevant_level:
                relevant_level -= 1 # next level will be lower, again we skip branches with shared parent
                ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(data[index]["id"])
                if ban_reason != None:
                    # one of direct parents/grandparents is already banned so not a new banned entry
                    return False
            index -= 1

        for index, id in enumerate(data, start=checked_position):
            ban_reason = self.get_reason_why_type_makes_object_invalid_primary_link(data[index]["id"])
            if ban_reason != None:
                #print("returning True")
                #print("00000000000000000000000000")
                return True
            if (index + 1) >= len(data):
                #print("00000000000000000000000000")
                return False
            if data[index + 1]["depth"] <= data[checked_position]["depth"]:
                #print(index, "+ 1", data[index + 1], "returning false")
                #print("00000000000000000000000000")
                return False

    def is_wikidata_type_id_recognised_as_OK(self, type_id):
        objects_mappable_in_OSM = [
            {'wikidata': 'Q486972', 'label': 'human settlement'},
            {'wikidata': 'Q811979', 'label': 'designed structure'},
            {'wikidata': 'Q46831', 'label': 'mountain range - geographic area containing numerous geologically related mountains'},
            {'wikidata': 'Q11776944', 'label': 'Megaregion'},
            {'wikidata': 'Q31855', 'label': 'instytut badawczy'},
            {'wikidata': 'Q34442', 'label': 'road'},
            {'wikidata': 'Q2143825', 'label': 'walking path path for hiking in a natural environment'},
            {'wikidata': 'Q11634', 'label': 'art of sculpture'},
            {'wikidata': 'Q56061', 'label': 'administrative territorial entity - territorial entity for administration purposes, with or without its own local government'},
            {'wikidata': 'Q473972', 'label': 'protected area'},
            {'wikidata': 'Q4022', 'label': 'river'},
            {'wikidata': 'Q22698', 'label': 'park'},
            {'wikidata': 'Q11446', 'label': 'ship'},
            {'wikidata': 'Q12876', 'label': 'tank'},
            {'wikidata': 'Q57607', 'label': 'christmas market'},
            {'wikidata': 'Q8502', 'label': 'mountain'},
            {'wikidata': 'Q10862618', 'label': 'mountain saddle'},
            {'wikidata': 'Q35509', 'label': 'cave'},
            {'wikidata': 'Q23397', 'label': 'lake'},
            {'wikidata': 'Q39816', 'label': 'valley'},
            {'wikidata': 'Q179700', 'label': 'statue'},
            # Quite generic ones
            {'wikidata': 'Q271669', 'label': 'landform'},
            {'wikidata': 'Q376799', 'label': 'transport infrastructure'},
            {'wikidata': 'Q15324', 'label': 'body of water'},
            {'wikidata': 'Q975783', 'label': 'land estate'},
            {'wikidata': 'Q8205328', 'label': 'equipment (human-made physical object with a useful purpose)'},
            {'wikidata': 'Q618123', 'label': 'geographical object'},
            {'wikidata': 'Q43229', 'label': 'organization'},
        ]
        for mappable_type in objects_mappable_in_OSM:
            if type_id == mappable_type['wikidata']:
                return True
        return False

    def wikidata_ids_of_countries_with_language(self, language_code):
        if language_code == "jp":
            return ['Q17']
        if language_code == "sv":
            return ['Q34']
        if language_code == "pl":
            return ['Q36']
        if language_code == "de":
            return ['Q183']
        if language_code == "cz":
            return ['Q213']
        if language_code == "it":
            vatican = 'Q237'
            san_marino = 'Q238'
            italy = 'Q38'
            return [vatican, san_marino, italy]
        if language_code == "tr": # turkish
            return ['Q43']
        if language_code == "bg":
            return ['Q219'] # Bulgaria
        if language_code == "uk": # ukrainian
            return ['Q212']
        if language_code == "ro": # romanian
            return ['Q218']
        if language_code == "sr": # Serbian (if I made mistake here please do not assume that I have some specific position in inis regional conflict)
            serbia = 'Q403'
            montenegro = 'Q236'
            bosnia_and_herzegovina = 'Q225'
            return [serbia, montenegro, bosnia_and_herzegovina]
        if language_code == "fa": # persian = farsi
            iran = 'Q794'
            afghanistan = 'Q889'
            tajikistan = 'Q863'
            return [iran, afghanistan, tajikistan]
        if language_code == "nl":
            netherlands = 'Q55'
            belgium = 'Q31' # one of three official
            return [netherlands, belgium]
        if language_code == "en":
            new_zealand = 'Q664'
            usa = 'Q30'
            uk = 'Q145'
            australia = 'Q408'
            canada = 'Q16'
            ireland = 'Q22890'
            # IDEA - add other areas from https://en.wikipedia.org/wiki/English_language
            return [uk, usa, new_zealand, australia, canada, ireland]
        assert False, "language code <" + language_code + "> without hardcoded list of matching countries"

    # unknown data, known to be completely inside -> not allowed, returns None
    # known to be outside or on border -> allowed, returns reason
    def why_object_is_allowed_to_have_foreign_language_label(self, object_description, wikidata_id):
        if wikidata_id == None:
            return "no wikidata entry exists"

        if self.expected_language_code == None:
            return "no expected language is defined"

        country_ids_where_expected_language_will_be_enforced = self.wikidata_ids_of_countries_with_language(self.expected_language_code)

        countries = self.get_country_location_from_wikidata_id(wikidata_id)
        if countries == None:
            # TODO locate based on coordinates...
            return None
        for country_id in countries:
            if country_id in country_ids_where_expected_language_will_be_enforced:
                continue
            country_name = wikidata_processing.get_wikidata_label(country_id, 'en')
            if country_name == None:
                return "it is at least partially in country without known name on Wikidata (country_id=" + country_id + ")"
            if country_id == 'Q7318':
                print(object_description + " is tagged on wikidata as location in no longer existing " + country_name)
                return None
            return "it is at least partially in " + country_name
        return None

    def get_country_location_from_wikidata_id(self, object_wikidata_id):
        countries = wikimedia_connection.get_property_from_wikidata(object_wikidata_id, 'P17')
        if countries == None:
            return None
        returned = []
        for country in countries:
            country_id = country['mainsnak']['datavalue']['value']['id']
            # we need to check whether locations still belongs to a given country
            # it is necessary to avoid gems like
            # "Płock is allowed to have foreign wikipedia link, because it is at least partially in Nazi Germany"
            # P582 indicates the time an item ceases to exist or a statement stops being valid
            # so statements qualified by P582 refer to the past
            try:
                country['qualifiers']['P582']
            except KeyError:
                    #P582 is missing, therefore it is not marked as a statement applying only to the past
                    returned.append(country_id)
        return returned

    def element_can_be_reduced_to_position_at_single_location(self, element):
        if element.get_element().tag == "relation":
            relation_type = element.get_tag_value("type")
            if relation_type == "person" or relation_type == "route":
                return False
        if element.get_tag_value("waterway") == "river":
            return False
        return True

    def object_should_be_deleted_not_repaired(self, object_type, tags):
        if object_type == "relation":
            if tags.get("type") == "person":
                return True
        if tags.get("historic") == "battlefield":
            return True


    def describe_osm_object(self, element):
        name = element.get_tag_value("name")
        if name == None:
            name = ""
        return name + " " + element.get_link()

    def is_wikipedia_page_geotagged(self, page):
        # <span class="latitude">50°04'02”N</span>&#160;<span class="longitude">19°55'03”E</span>
        index = page.find("<span class=\"latitude\">")
        inline = page.find("coordinates inline plainlinks")
        if index > inline != -1:
            index = -1  #inline coordinates are not real ones
        if index == -1:
            kml_data_str = "><span id=\"coordinates\"><b>Route map</b>: <a rel=\"nofollow\" class=\"external text\""
            if page.find(kml_data_str) == -1:  #enwiki article links to area, not point (see 'Central Park')
                return False
        return True
