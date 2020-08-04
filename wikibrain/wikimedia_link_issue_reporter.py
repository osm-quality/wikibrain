import wikimedia_connection.wikimedia_connection as wikimedia_connection
import wikimedia_connection.wikidata_processing as wikidata_processing
import geopy.distance
import re
import yaml
from wikibrain import wikipedia_knowledge

class ErrorReport:
    def __init__(self, error_message=None, desired_wikipedia_target=None, debug_log=None, error_id=None, prerequisite=None, extra_data=None, proposed_tagging_changes=None):
        self.error_id = error_id
        self.error_message = error_message
        self.debug_log = debug_log
        self.current_wikipedia_target = None #TODO - eliminate, start from wikipedia validator using this data
        self.desired_wikipedia_target = desired_wikipedia_target  #TODO - eliminate, start from wikipedia validator using this data
        self.prerequisite = prerequisite
        self.extra_data = extra_data # TODO - replace by more specific
        self.proposed_tagging_changes = proposed_tagging_changes
        self.osm_object_url = None
        self.location = None

    def bind_to_element(self, element):
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
            debug_log = self.debug_log,
            osm_object_url = self.osm_object_url,
            current_wikipedia_target = self.current_wikipedia_target, #TODO - eliminate, start from wikipedia validator using this data
            desired_wikipedia_target = self.desired_wikipedia_target, #TODO - eliminate, start from wikipedia validator using this data
            proposed_tagging_changes = self.proposed_tagging_changes,
            extra_data = self.extra_data,
            prerequisite = self.prerequisite,
            location = self.location,
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
            return self.get_wikipedia_from_wikidata_assume_no_old_style_wikipedia_tags(tags.get('wikidata'))

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

    def freely_reorderable_issue_reports(self, object_description, location, tags):
        wikipedia = self.get_effective_wikipedia_tag(tags)
        wikidata_id = self.get_effective_wikidata_tag(tags)
        # Note that wikipedia may be None - maybe there is just a Wikidata entry!
        # Note that wikidata_id may be None - maybe it was not created yet! 

        # IDEA links from buildings to parish are wrong - but from religious admin are OK https://www.wikidata.org/wiki/Q11808149

        something_reportable = self.get_problem_based_on_wikidata_blacklist(wikidata_id, wikidata_id, wikipedia)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.get_problem_based_on_wikidata_and_osm_element(object_description, location, wikidata_id)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.get_wikipedia_language_issues(object_description, tags, wikipedia, wikidata_id)
        if something_reportable != None:
            return something_reportable

        something_reportable = self.check_is_object_is_existing(wikidata_id)
        if something_reportable != None:
            return something_reportable

        return None

    def wikidata_connection_blacklisted_and_unfixable(self):
        return [
            'Q1456883',
        ]

    def wikidata_connection_blacklist(self):
        return {
            'Q5686673': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cinema'}, 'name': 'Cinepolis'},
            'Q5416698': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cinema'}, 'name': 'Event'},
            'Q3060526': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cinema'}, 'name': 'Pathé Gaumont'},
            'Q5579784': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cinema'}, 'name': 'Golden Screen Cinemas'},
            'Q17053599': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cinema'}, 'name': 'MBO Cinemas'},

            'Q4778364': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'Anytime Fitness'},
            'Q21015663': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'CorePower Yoga'},
            'Q5196080': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'Curves'},
            'Q6457180': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'LA Fitness'},
            'Q30930959': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'Smart Fit'},
            'Q4013942': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'Virgin Active'},
            'Q3204640': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': "L'Orange Bleue"},
            'Q11310515': {'prefix': 'brand:', 'expected_tags': {'leisure': 'fitness_centre'}, 'name': 'ジョイフィット'},

            'Q668687': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'United States Postal Service'},
            'Q373724': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}},
            'Q3181430': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}},
            'Q1502763': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}},
            'Q2662336': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Белпошта'},
            'Q459477': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'FedEx'},
            'Q12133863': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Нова Пошта'},
            'Q1066476': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': '中国邮政'},
            'Q1032001': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Canada Post'},
            'Q746263': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Казпочта'},
            'Q489815': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'DHL'},
            'Q909429': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'CTT'},
            'Q5172893': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Correos de Chile'},
            'Q776605': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Oficina de Correos'},
            'Q157645': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Deutsche Post'},
            'Q1024518': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'CTT'},
            'Q1613532': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Hermes Paketshop'},
            'Q1139182': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Mail Boxes Etc.'},
            'Q1406037': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'PHLPost'},
            'Q1783168': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Post Office'},
            'Q7771029': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'The UPS Store'},
            'Q482490': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'An Post'},
            'Q843453': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Posti'},
            'Q1275135': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'ΕΛΤΑ'},
            'Q6584353': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'ヤマト運輸'},
            'Q2470783': {'prefix': 'brand:', 'expected_tags': {'amenity': 'post_office'}, 'name': 'Укрпошта'},

            'Q474379': {'prefix': 'brand:', 'expected_tags': {'shop': 'copyshop'}, 'name': 'FedEx Office'},

            'Q889624': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Leroy Merlin'},
            'Q10541151': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Jula'},
            'Q1373493': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Lowe\'s'},
            'Q864407': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Home Depot', 'allowed_tags': {'name': 'The Home Depot'}},
            'Q4672981': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Ace Hardware'},
            'Q2510786': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Brico'},
            'Q2925147': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Bricomarché'},
            'Q2925146': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Bricorama'},
            'Q5331091': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Easy'},
            'Q3139611': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Home Building Centre'},
            'Q3139611': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Home Hardware Building Centre'},
            'Q3355552': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Biltema'},
            'Q3117467': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'Lapeyre'},
            'Q11301462': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'ケーヨー'},
            'Q11303403': {'prefix': 'brand:', 'expected_tags': {'shop': 'doityourself'}, 'name': 'コーナン'},

            'Q679750': {'prefix': 'brand:', 'expected_tags': {'shop': 'hardware'}, 'name': 'Würth'},

            'Q3196672': {'prefix': 'brand:', 'expected_tags': {'shop': 'tool_hire'}, 'name': 'Kiloutou'},

            'Q54078': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'IKEA'},
            'Q4805437': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Ashley Furniture HomeStore'},
            'Q1991755': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Casa'},
            'Q138913': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Dänisches Bettenlager'},
            'Q138913': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'JYSK'},
            'Q3280364': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Maisons du Monde'},
            'Q877547': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Möbelix'},
            'Q7313497': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Rent-A-Center'},
            'Q10801453': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'ニトリ'},
            'Q541134': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Conforama'},
            'Q5178707': {'prefix': 'brand:', 'expected_tags': {'shop': 'furniture'}, 'name': 'Courts'},

            'Q18629057': {'prefix': 'brand:', 'expected_tags': {'shop': 'bed'}, 'name': 'Matratzen Concord'},

            'Q17026595': {'prefix': 'brand:', 'expected_tags': {'shop': 'tiles'}, 'name': 'Topps Tiles'},

            'Q7191691': {'prefix': 'brand:', 'expected_tags': {'shop': 'interior_decoration'}, 'name': 'Pier 1 Imports'},

            'Q5522290': {'prefix': 'brand:', 'expected_tags': {'shop': 'houseware'}, 'name': 'At Home'},

            'Q17635288': {'prefix': 'brand:', 'expected_tags': {'shop': 'fabric'}, 'name': 'Mondial Tissus'},

            'Q3007012': {'prefix': 'brand:', 'expected_tags': {'shop': 'kitchen'}, 'name': 'Cuisinella'},
            'Q3317571': {'prefix': 'brand:', 'expected_tags': {'shop': 'kitchen'}, 'name': 'Mobalpa'},

            'Q2241604': {'prefix': 'brand:', 'expected_tags': {'shop': 'jewelry'}, 'name': 'Pandora'},

            'Q919641': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Verizon Wireless'},
            'Q118046': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Carphone Warehouse'},
            'Q3306167': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'MEO'},
            'Q865038': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Optus'},
            'Q1431486': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Orange'},
            'Q118046': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Phone House'},
            'Q218765': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'SFR'},
            'Q309865': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Tele2'},
            'Q9396': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Telekom'},
            'Q2466256': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'U.S. Cellular'},
            'Q122141': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Vodafone'},
            'Q65310': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Евросеть'},
            'Q65371': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Связной'},
            'Q5322556': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'ワイモバイル'},
            'Q160120': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Huawei'},
            'Q402880': {'prefix': 'brand:', 'expected_tags': {'shop': 'mobile_phone'}, 'name': 'Билайн'},

            'Q815694': {'prefix': 'brand:', 'expected_tags': {'shop': 'telecommunication'}, 'name': 'Bell'},
            'Q1368919': {'prefix': 'brand:', 'expected_tags': {'shop': 'telecommunication'}, 'name': 'МТС'},
            'Q1640639': {'prefix': 'brand:', 'expected_tags': {'shop': 'telecommunication'}, 'name': 'TMpoint'},
            'Q1477012': {'prefix': 'brand:', 'expected_tags': {'shop': 'telecommunication'}, 'name': 'Ростелеком'},
            'Q1505321': {'prefix': 'brand:', 'expected_tags': {'shop': 'telecommunication'}, 'name': 'Укртелеком'},
            'Q402880': {'prefix': 'brand:', 'expected_tags': {'office': 'telecommunication'}, 'name': 'Beeline'},
            'Q402880': {'prefix': 'brand:', 'expected_tags': {'office': 'telecommunication'}, 'name': 'Билайн'},

            'Q533415': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Best Buy'},
            'Q2921695': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Boulanger'},
            'Q17050121': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Elgiganten'},
            'Q680990': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Expert'},
            'Q5401467': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Frávega'},
            'Q6167713': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Jaycar'},
            'Q7117161': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'P. C. Richard & Son'},
            'Q20857751': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Power'},
            'Q7343720': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Robert Dyas'},
            'Q2543504': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Saturn'},
            'Q7737217': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'The Good Guys'},
            'Q6322472': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'ケーズデンキ'},
            'Q1096390': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'ヤマダ電機'},
            'Q2439098': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Darty'},
            'Q6558800': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'М.Видео'},
            'Q55632855': {'prefix': 'brand:', 'expected_tags': {'shop': 'electronics'}, 'name': 'Senheng'},

            'Q7330409': {'prefix': 'brand:', 'expected_tags': {'shop': 'hifi'}, 'name': 'Richer Sounds'},

            'Q4036922': {'prefix': 'brand:', 'expected_tags': {'shop': 'computer'}, 'name': 'DNS'},
            'Q3117461': {'prefix': 'brand:', 'expected_tags': {'shop': 'computer'}, 'name': 'LDLC'},

            'Q7547351': {'prefix': 'brand:', 'expected_tags': {'shop': 'photo'}, 'name': 'Snappy Snaps'},

            'Q5495932': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Fred Meyer'},
            'Q552652': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Netto'},
            'Q11694239': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Dino'},
            'Q857182': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Biedronka'},
            'Q487494': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Tesco'},
            'Q685967': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Kaufland'},
            'Q151954': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Lidl', 'allowed_tags': {'name:es': 'Lidl'}},
            'Q125054': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Aldi'},
            'Q610492': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Spar'},
            'Q537781': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Billa'},
            'Q610492': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Spar'},
            'Q12047031': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Prisma'},
            'Q483551': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Walmart', 'allowed_tags': {'name': 'Walmart Supercenter'}},
            'Q701755': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Edeka'},
            'Q701755': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Treff 3000'},
            'Q2181426': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Leader Price'},
            'Q518563': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Konzum'},
            'Q2818601': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': '8 à Huit'},
            'Q4646307': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': '99 Ranch Market'},
            'Q4712282': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Albertsons'},
            'Q41171373': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Aldi Nord'},
            'Q28679415': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Assaí Atacadista'},
            'Q2868739': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Atacadão'},
            'Q758603': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Auchan'},
            'Q2870659': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Auchan Drive'},
            'Q3631008': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Big Bazaar'},
            'Q858665': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Big C'},
            'Q779845': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'CBA'},
            'Q2940187': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Carrefour City'},
            'Q2689639': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Carrefour Market'},
            'Q432564': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Coop'},
            'Q5175072': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Costcutter'},
            'Q5274978': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Dierbergs'},
            'Q1435950': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Food Lion'},
            'Q50737403': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Fresh'},
            'Q3504731': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'G20'},
            'Q4217013': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Giant Hypermarket'},
            'Q1380537': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Géant Casino'},
            'Q5665067': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Harris Teeter'},
            'Q1663776': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'ICA'},
            'Q1663776': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'ICA Kvantum'},
            'Q1663776': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'ICA Maxi'},
            'Q3146662': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'IGA'},
            'Q3213589': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'La Vie Claire'},
            'Q21008564': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Londis'},
            'Q714491': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'M&S Foodhall'},
            'Q714491': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'M&S Simply Food'},
            'Q2079198': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Market Basket'},
            'Q680727': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Migros'},
            'Q6910891': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'More'},
            'Q922344': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Morrisons'},
            'Q2720988': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Netto'},
            'Q450180': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Norma'},
            'Q284688': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Penny'},
            'Q7242574': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Price Chopper'},
            'Q672170': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Publix'},
            'Q3484790': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Punto Simply'},
            'Q3929820': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Ralphs'},
            'Q7419620': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Santa Isabel'},
            'Q3484790': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Simply Market'},
            'Q1129779': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Sky'},
            'Q3277439': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'The Co-operative Food'},
            'Q7941609': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Vons'},
            'Q1809448': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Whole Foods Market'},
            'Q8023592': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'WinCo Foods'},
            'Q1264366': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Winn-Dixie'},
            'Q3249145': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Woolworths'},
            'Q2529029': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Hyper U'},
            'Q16968817': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Rewe'},
            'Q16968817': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Rewe City'},
            'Q2529029': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Super U'},
            'Q2529029': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'U Express'},
            'Q2868738': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Атак'},
            'Q11924747': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Bonpreu'},
            'Q61070539': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Covirán'},
            'Q879858': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Netto Marken-Discount'},
            'Q55641396': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Patel Brothers'},
            'Q3771177': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Selver'},
            'Q1504903': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'V-MARKT'},
            'Q2565040': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Евроопт'},
            'Q4301704': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Монетка'},
            'Q940518': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Магнит'},
            'Q1768969': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Пятёрочка'},
            'Q4419434': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Сільпо'},
            'Q12165977': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Фора'},
            'Q11280900': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'ゆめタウン'},
            'Q11283128': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'アコレ'},
            'Q11331715': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'イオンマーケット'},
            'Q3088746': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'イトーヨーカドー'},
            'Q11293184': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'オーケーストア'},
            'Q11305129': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'サミット'},
            'Q11340902': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'マミーマート'},
            'Q11346201': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'ヨークマート'},
            'Q11346476': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'ライフ'},
            'Q706247': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': '惠康 Wellcome'},
            'Q3108542': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': '西友'},
            'Q706247': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': '頂好'},
            'Q706247': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': '頂好超市'},
            'Q1613639': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Kiwi'},
            'Q2719231': {'prefix': 'brand:', 'expected_tags': {'shop': 'supermarket'}, 'name': 'Monoprix'},

            'Q715583': {'prefix': 'brand:', 'expected_tags': {}, 'name': 'Costco'},
            'Q1508234': {'prefix': 'brand:', 'expected_tags': {}, 'name': 'Safeway'},

            'Q1941209': {'prefix': 'brand:', 'expected_tags': {}, 'name': 'Mlekpol'},

            'Q564213': {'prefix': 'brand:', 'expected_tags': {'shop': 'coffee'}, 'name': 'Tchibo'},
            
            'Q37158': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Starbucks'},
            'Q11305989': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'サンマルクホールディングス', 'allowed_tags': {'name:ja': 'サンマルクホールディングス', 'name:ja_rm': 'Sanmaruku Kafe'}},
            'Q11294597': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'サンマルクカフェ', 'allowed_tags': {'name:ja': 'サンマルクカフェ', 'name:ja_rm': 'Kafe Berōche'}},
            'Q4906876': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Biggby Coffee'},
            'Q4928917': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Blue Bottle Coffee'},
            'Q23461358': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Boston Tea Party'},
            'Q5017235': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Cafe Coffee Day'},
            'Q675808': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Caffè Nero'},
            'Q43247503': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Café Amazon'},
            'Q608845': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Costa'},
            'Q5581670': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Gong Cha'},
            'Q5581670': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Gong Cha'},
            'Q22101966': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Patisserie Valerie'},
            'Q30891188': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Шоколадница'},
            'Q11322732': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'ドトールコーヒーショップ'},
            'Q16540032': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Café Martínez'},
            'Q7085308': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'OldTown White Coffee'},
            'Q95722097': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': 'Tealive'},
            'Q60875376': {'prefix': 'brand:', 'expected_tags': {'amenity': 'cafe'}, 'name': '喜茶'},

            'Q4979810': {'prefix': 'brand:', 'expected_tags': {'amenity': 'ice_cream'}, 'name': "Bruster's Ice Cream"},
            'Q17020087': {'prefix': 'brand:', 'expected_tags': {'amenity': 'ice_cream'}, 'name': 'Marble Slab Creamery'},

            'Q15178238': {'prefix': 'brand:', 'expected_tags': {'shop': 'confectionery'}, 'name': 'Adyar Ananda Bhavan'},
            'Q17123688': {'prefix': 'brand:', 'expected_tags': {'shop': 'confectionery'}, 'name': 'Hussel'},
            'Q61742027': {'prefix': 'brand:', 'expected_tags': {'shop': 'confectionery'}, 'name': 'Красный пищевик'},
            'Q11307696': {'prefix': 'brand:', 'expected_tags': {'shop': 'confectionery'}, 'name': 'シャトレーゼ'},

            'Q80335': {'prefix': 'brand:', 'expected_tags': {'shop': 'chocolate'}, 'name': 'Leonidas'},
            'Q152822': {'prefix': 'brand:', 'expected_tags': {'shop': 'chocolate'}, 'name': 'Lindt'},

            'Q2453627': {'prefix': 'brand:', 'expected_tags': {'shop': 'beverages'}, 'name': 'Trinkgut'},

            'Q2589061': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Żabka'},
            'Q3268010': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Circle K'},
            'Q259340': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': '7-Eleven', 'allowed_tags': {'name:en': '7-Eleven'}},
            'Q3408522': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Proxi'},
            'Q16968817': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Rewe To Go'},
            'Q4650251': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'ABC'},
            'Q12580836': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'CU'},
            'Q624041': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'GS25'},
            'Q18154470': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Minit Mart'},
            'Q10851968': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'OK超商'},
            'Q940518': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Магнит'},
            'Q4419434': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'Сильпо'},
            'Q11313419': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'スリーエフ'},
            'Q11314123': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'セイコーマート'},
            'Q5209392': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'デイリーヤマザキ'},
            'Q11345131': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'ヤマザキショップ'},
            'Q11350960': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'ローソンストア100'},
            'Q24866804': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'ローソン・スリーエフ'},
            'Q10891564': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': '全家便利商店'},
            'Q17147574': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'myNEWS.com'},
            'Q66480830': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'uSmile 昆仑好客'},
            'Q16141064': {'prefix': 'brand:', 'expected_tags': {'shop': 'convenience'}, 'name': 'サンクス'},

            'Q798298': {'prefix': 'brand:', 'expected_tags': {'shop': 'bakery'}, 'name': 'Backwerk'},
            'Q42825993': {'prefix': 'brand:', 'expected_tags': {'shop': 'bakery'}, 'name': 'Bäckerei Fuchs'},
            'Q1192443': {'prefix': 'brand:', 'expected_tags': {'shop': 'bakery'}, 'name': 'Der Beck'},

            'Q316004': {'prefix': 'brand:', 'expected_tags': {'shop': 'chemist'}, 'name': 'Rossmann'},
            'Q1958759': {'prefix': 'brand:', 'expected_tags': {'shop': 'chemist'}, 'name': 'Müller'},

            'Q202210': {'prefix': 'brand:', 'expected_tags': {'shop': 'video_games'}, 'name': 'GameStop'},
            'Q3312221': {'prefix': 'brand:', 'expected_tags': {'shop': 'video_games'}, 'name': 'Micromania'},

            'Q5433297': {'prefix': 'brand:', 'expected_tags': {'shop': 'video'}, 'name': 'Family Video'},
            'Q5533938': {'prefix': 'brand:', 'expected_tags': {'shop': 'video'}, 'name': 'ゲオ'},

            'Q2884670': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': "Barnardo's"},
            'Q4970039': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'British Heart Foundation'},
            'Q326079': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'Cancer Research UK'},
            'Q5583655': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'Goodwill'},
            'Q1636581': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'Humana'},
            'Q267941': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'Oxfam'},
            'Q7165541': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'PDSA'},
            'Q7634271': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'Sue Ryder'},
            'Q7722484': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': "The Children's Society"},
            'Q188307': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'The Salvation Army'},
            'Q157169': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'YMCA'},
            'Q864933': {'prefix': 'brand:', 'expected_tags': {'shop': 'chemist'}, 'name': 'Bipa'},
            'Q266572': {'prefix': 'brand:', 'expected_tags': {'shop': 'chemist'}, 'name': 'dm'},
            'Q215934': {'prefix': 'brand:', 'expected_tags': {'shop': 'charity'}, 'name': 'Save the Children'},

            'Q2895789': {'prefix': 'brand:', 'expected_tags': {'amenity': 'social_centre'}, 'name': 'Elks Lodge'},
            'Q3270231': {'prefix': 'brand:', 'expected_tags': {'amenity': 'social_centre'}, 'name': 'Royal Canadian Legion Hall'},
            'Q3556413': {'prefix': 'brand:', 'expected_tags': {'amenity': 'social_centre'}, 'name': 'VFW Post'},

            'Q2923055': {'prefix': 'brand:', 'expected_tags': {'amenity': 'social_facility'}, 'name': 'Boys & Girls Club'},

            'Q11628761': {'prefix': 'brand:', 'expected_tags': {'shop': 'baby_goods'}, 'name': '西松屋'},

            'Q188326': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'H&M'},
            'Q701338': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'C&A'},
            'Q689695': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Tally Weijl'},
            'Q3177174': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Jennyfer'},
            'Q63063871': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Caroll'},
            'Q634881': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Tommy Hilfiger'},
            'Q3442791': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Ross'},
            'Q927272': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'NKD'},
            'Q6793571': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Maurices'},
            'Q136503': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Mango'},
            'Q11661241': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': '洋服の青山'},
            'Q26070': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'ユニクロ'},
            'Q3122954': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Gémo'},
            'Q2988422': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Canada Goose'},
            'Q542767': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Dior'},
            'Q50540636': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Camp David'},
            'Q2700576': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Gina Laura'},
            'Q12063852': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'New Look'},
            'Q873447': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Gerry Weber'},
            'Q18640136': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'mister*lady'},
            'Q1027874': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Calzedonia'},
            'Q5298588': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Dorothy Perkins'},
            'Q26070': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Uniqlo'},
            'Q83750': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Desigual'},
            'Q2934647': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Camaïeu'},
            'Q1371302': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Takko'},
            'Q2735242': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Old Navy'},
            'Q2475146': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Ulla Popken'},
            'Q1686071': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Jeans Fritz'},
            'Q11189480': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'AOKI'},
            'Q3196299': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Kiabi'},
            'Q706421': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'New Yorker'},
            'Q265056': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 's.Oliver'},
            'Q3025542': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Devred'},
            'Q23823668': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'TK Maxx'},
            'Q691029': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Pull & Bear'},
            'Q571206': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Tom Tailor'},
            'Q1758066': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Pimkie'},
            'Q3350027': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Okaïdi'},
            'Q594721': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Vero Moda'},
            'Q883245': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Orsay'},
            'Q532746': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Esprit'},
            'Q883965': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'KiK'},
            'Q1290088': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Engbers'},
            'Q1361016': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': "Ernsting's family"},
            'Q147662': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Zara'},
            'Q1684445': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Superdry'},
            'Q2672003': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Celio'},
            'Q12061509': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Matalan'},
            'Q7377762': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'rue21'},
            'Q892598': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Bonita'},
            'Q3059202': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Etam'},
            'Q6077665': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Jack & Jones'},
            'Q7157762': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Peacocks'},
            'Q309031': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Lacoste'},
            'Q671216': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Triumph'},
            'Q300220': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'AWG-Modecenter'},
            'Q2861975': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Armand Thiery'},
            'Q306457': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'French Connection'},
            'Q9294202': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'House'},
            'Q6711808': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'M&Co'},
            'Q6718117': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'MS Mode'},
            'Q25381083': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Mark Formelle'},
            'Q16648226': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': "Women'secret"},
            'Q5184783': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Crew Clothing Company'},
            'Q3040318': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Du Pareil au Même'},
            'Q1783759': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Kookaï'},
            'Q3574548': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Zadig & Voltaire'},
            'Q11340456': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'マックハウス'},
            'Q2102562': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'POLO'},
            'Q2021416': {'prefix': 'brand:', 'expected_tags': {'shop': 'clothes'}, 'name': 'Volcom'},

            'Q1095857': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'Clarks'},
            'Q664543': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'Deichmann'},
            'Q1280255': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'Ecco'},
            'Q16993893': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'G.H. Bass & Co.'},
            'Q2144204': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'Reno'},
            'Q3946053': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'Salvatore Ferragamo'},
            'Q2800720': {'prefix': 'brand:', 'expected_tags': {'shop': 'shoes'}, 'name': 'Siemes Schuhcenter'},

            'Q2817899': {'prefix': 'brand:', 'expected_tags': {'shop': 'dry_cleaning'}, 'name': '5àsec'},
            'Q11579995': {'prefix': 'brand:', 'expected_tags': {'shop': 'dry_cleaning'}, 'name': '白洋舎'},

            'Q1880676': {'prefix': 'brand:', 'expected_tags': {'shop': 'cosmetics'}, 'name': "L'Occitane"},
            'Q3342592': {'prefix': 'brand:', 'expected_tags': {'shop': 'cosmetics'}, 'name': 'Nocibé'},
            'Q2408041': {'prefix': 'brand:', 'expected_tags': {'shop': 'cosmetics'}, 'name': 'Sephora'},
            'Q837851': {'prefix': 'brand:', 'expected_tags': {'shop': 'cosmetics'}, 'name': 'The Body Shop'},
            'Q18400706': {'prefix': 'brand:', 'expected_tags': {'shop': 'cosmetics'}, 'name': "Л'Этуаль"},

            'Q28496595': {'prefix': 'brand:', 'expected_tags': {'shop': 'beauty'}, 'name': 'Yves Rocher'},
            
            'Q1129073': {'prefix': 'brand:', 'expected_tags': {'shop': 'perfumery'}, 'name': 'Marionnaud'},

            'Q1046951': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Target'},
            'Q5135229': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Falabella'},
            'Q4876153': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Bealls'},
            'Q4902331': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Bi-Mart'},
            'Q4905973': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Big Lots'},
            'Q5558429': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Giant Tiger'},
            'Q4040441': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Harvey Norman'},
            'Q5928422': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'House of Fraser'},
            'Q382686': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Manor'},
            'Q708789': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Muji'},
            'Q1535260': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Printemps'},
            'Q183538': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Woolworth'},
            'Q629269': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': "Macy's"},
            'Q174310': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'Nordstrom'},
            'Q10860683': {'prefix': 'brand:', 'expected_tags': {'shop': 'department_store'}, 'name': 'TJ Maxx'},

            'Q3033947': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Dollarama'},
            'Q2634111': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Action'},
            'Q1434528': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Poundland'},
            'Q4836931': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'B&M Bargains'},
            'Q7235675': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Poundstretcher'},
            'Q20732498': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Miniso'},
            'Q5433101': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Family Dollar'},
            'Q5289230': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Dollar Tree'},
            'Q5888229': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Home Bargains'},
            'Q1364603': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'TEDi'},
            'Q145168': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Dollar General'},
            'Q4038791': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Fix Price'},
            'Q5455836': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'Five Below'},
            'Q3209040': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': "La Foir'Fouille"},
            'Q65079443': {'prefix': 'brand:', 'expected_tags': {'shop': 'variety_store'}, 'name': 'OneBelow'},

            'Q3007154': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': 'Cultura'},
            'Q3045978': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': 'Empik'},
            'Q795454': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': 'Barnes & Noble'},
            'Q1866547': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': 'Bertrand'},
            'Q1548712': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': 'WHSmith'},
            'Q893011': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': 'ブックオフ'},
            'Q10866539': {'prefix': 'brand:', 'expected_tags': {'shop': 'books'}, 'name': '三省堂書店'},

            'Q18385014': {'prefix': 'brand:', 'expected_tags': {'shop': 'stationery'}, 'name': 'Bureau Vallée'},
            'Q1915329': {'prefix': 'brand:', 'expected_tags': {'shop': 'stationery'}, 'name': 'McPaper'},
            'Q7079486': {'prefix': 'brand:', 'expected_tags': {'shop': 'stationery'}, 'name': 'Officeworks'},
            
            'Q5874938': {'prefix': 'brand:', 'expected_tags': {'shop': 'craft'}, 'name': 'Hobby Lobby'},
            'Q22026341': {'prefix': 'brand:', 'expected_tags': {'shop': 'craft'}, 'name': 'Woodcraft'},

            'Q7179258': {'prefix': 'brand:', 'expected_tags': {'shop': 'pet'}, 'name': 'Pets at Home'},
            'Q875796': {'prefix': 'brand:', 'expected_tags': {'shop': 'pet'}, 'name': 'Fressnapf'},
            'Q3307147': {'prefix': 'brand:', 'expected_tags': {'shop': 'pet'}, 'name': 'PetSmart'},
            'Q875796': {'prefix': 'brand:', 'expected_tags': {'shop': 'pet'}, 'name': 'Maxi Zoo'},
            'Q7171563': {'prefix': 'brand:', 'expected_tags': {'shop': 'pet'}, 'name': 'Pet Supplies Plus'},

            'Q56729186': {'prefix': 'brand:', 'expected_tags': {'shop': 'travel_agency'}, 'name': 'DER Reisebüro'},
            'Q6109053': {'prefix': 'brand:', 'expected_tags': {'shop': 'travel_agency'}, 'name': 'JTB'},
            'Q2141800': {'prefix': 'brand:', 'expected_tags': {'shop': 'travel_agency'}, 'name': 'Thomas Cook'},
            'Q4548': {'prefix': 'brand:', 'expected_tags': {'shop': 'travel_agency'}, 'name': 'Turkish Airlines'},
            
            'Q2040264': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'City Union Bank'},
            'Q1160928': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'mBank'},
            'Q2003549': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Axis Bank', 'allowed_tags': {'name:en': 'Axis Bank'}},
            'Q631047': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'HDFC Bank', 'allowed_tags': {'short_name': 'HDFC'}},
            'Q2003777': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Canara Bank'},
            'Q2005310': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'UCO Bank', 'allowed_tags': {'name:en': 'UCO Bank'}},
            'Q2003237': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'United Bank of India', 'allowed_tags': {'short_name': 'UBI', 'name:en': 'United Bank of India'}},
            'Q2040394': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Yes Bank', 'allowed_tags': {'name:en': 'Yes Bank'}},
            'Q487907': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank of America'},
            'Q2040404': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Kotak Mahindra Bank', 'allowed_tags': {'name:en': 'Kotak Mahindra Bank'}},
            'Q2040323': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'IndusInd Bank', 'allowed_tags': {'name:en': 'IndusInd Bank'}},
            'Q2018840': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Allahabad Bank', 'allowed_tags': {'name:en': 'Allahabad Bank'}},
            'Q3595747': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Dena Bank', 'allowed_tags': {'name:en': 'Dena Bank'}},
            'Q6373724': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Karur Vysya Bank', 'allowed_tags': {'name:en': 'Karur Vysya Bank', 'short_name': 'KVB'}},
            'Q2004078': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Union Bank of India', 'allowed_tags': {'name:en': 'Union Bank of India', 'short_name': 'UBI'}},
            'Q367008': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Oriental Bank of Commerce', 'allowed_tags': {'name:en': 'Oriental Bank of Commerce', 'short_name': 'OBC'}},
            'Q2003302': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Punjab & Sind Bank', 'allowed_tags': {'name:en': 'Punjab & Sind Bank'}},
            'Q2004304': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank of Maharashtra', 'allowed_tags': {'name:en': 'Bank of Maharashtra'}},
            'Q739084': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'U.S. Bank'},
            'Q1740314': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'KeyBank'},
            'Q744149': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Wells Fargo'},
            'Q524629': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Chase Bank'},
            'Q5266685': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'DCB Bank'},
            'Q6479935': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Lakshmi Vilas Bank'},
            'Q3633485': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'IDBI Bank'},
            'Q2007090': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Central Bank of India'},
            'Q499707': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BNP Paribas'},
            'Q2931752': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'CNEP'},
            'Q11710978': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Idea Bank'},
            'Q2044983': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Federal Bank', 'allowed_tags': {'name:en': 'Federal Bank'}},
            'Q2003476': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Andhra Bank', 'allowed_tags': {'name:en': 'Andhra Bank'}},
            'Q2003387': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Corporation Bank', 'allowed_tags': {'name:en': 'Corporation Bank'}},
            'Q2003789': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Indian Bank', 'allowed_tags': {'name:en': 'Indian Bank'}},
            'Q270363': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Société Générale'},
            'Q2003611': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Indian Overseas Bank'},
            'Q41680844': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Volksbank'},
            'Q2004439': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank of India'},
            'Q205012': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Sberbank'},
            'Q2003797': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank of Baroda'},
            'Q2876788': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BBVA Francés'},
            'Q4742758': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'America First Credit Union'},
            'Q487230': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '신한은행'},
            'Q625531': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'SC제일은행'},
            'Q1991373': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Белагропромбанк'},
            'Q4189507': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Cathay Bank'},
            'Q7314386': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Republic Bank'},
            'Q3350382': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Sonali Bank'},
            'Q4034833': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank Al Habib'},
            'Q8254971': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Cajamar'},
            'Q7887504': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'UBL'},
            'Q2744340': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '横浜銀行'},
            'Q4476693': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Уралсиб'},
            'Q4835409': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BECU'},
            'Q571997': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '新生銀行'},
            'Q1377835': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Альфа-Банк'},
            'Q15982510': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'MCB'},
            'Q702656': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '國泰世華商業銀行'},
            'Q4426566': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Совкомбанк'},
            'Q795504': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BBBank'},
            'Q4304446': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Мособлбанк'},
            'Q2882083': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BCI'},
            'Q4086829': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Бинбанк'},
            'Q2666775': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'בנק הפועלים'},
            'Q1442804': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Union Bank'},
            'Q4327204': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Открытие'},
            'Q2335199': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Macro'},
            'Q4191388': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Зенит'},
            'Q962865': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'ธนาคารกรุงไทย'},
            'Q1940058': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Mittelbrandenburgische Sparkasse'},
            'Q1667302': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bicici'},
            'Q988284': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '三菱UFJ銀行'},
            'Q66048': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Deutsche Bank'},
            'Q2038986': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'ธนาคารไทยพาณิชย์'},
            'Q2900227': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'בנק ירושלים'},
            'Q252004': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Rabobank'},
            'Q846735': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Nationwide'},
            'Q548278': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Standard Chartered'},
            'Q4781125': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Apple Bank'},
            'Q1636974': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Danske Bank'},
            'Q1573140': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Hamburger Sparkasse'},
            'Q26298': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '农业银行'},
            'Q861042': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Western Union'},
            'Q9581725': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'ActivoBank'},
            'Q4854124': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BCP'},
            'Q790068': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '中国银行'},
            'Q16920636': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'United Bank'},
            'Q4500466': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Хоум Кредит'},
            'Q3006236': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Crédit Mutuel de Bretagne'},
            'Q1476162': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'UBI Banca'},
            'Q4304145': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Московский индустриальный банк'},
            'Q3385268': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Santander Río'},
            'Q642627': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Crédit Mutuel'},
            'Q3550305': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'UIB'},
            'Q4732553': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Allied Bank'},
            'Q806639': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank Mandiri'},
            'Q835283': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Caixa Econômica Federal'},
            'Q2009139': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Oberbank'},
            'Q2740021': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'NatWest'},
            'Q3310164': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Halifax'},
            'Q690739': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BIAT'},
            'Q2877455': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BRED'},
            'Q20013358': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco Agrario'},
            'Q5718188': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco Estado'},
            'Q2917708': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco Nacional'},
            'Q806206': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bancolombia'},
            'Q806807': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bankia'},
            'Q846647': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banque Populaire'},
            'Q2883441': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banque Populaire'},
            'Q245343': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Barclays'},
            'Q806181': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bradesco'},
            'Q1023306': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'CEC Bank'},
            'Q746525': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'CIC'},
            'Q3006220': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'CIH Bank'},
            'Q1547738': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': "Caisse d'Épargne"},
            'Q857063': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Citibank'},
            'Q1114148': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Comerica Bank'},
            'Q157617': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Commerzbank'},
            'Q389872': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Crelan'},
            'Q5289205': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Dollar Bank'},
            'Q806175': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'EuroBic'},
            'Q5717952': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Galicia'},
            'Q190464': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'HSBC'},
            'Q645708': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'ING'},
            'Q5558589': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Mibanco'},
            'Q17488861': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Novo Banco'},
            'Q708835': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Postbank'},
            'Q4854101': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco Mercantil'},
            'Q517093': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco de Venezuela'},
            'Q160126': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'RBS'},
            'Q975655': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'SEB'},
            'Q5835668': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Santander'},
            'Q3488479': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Société Marseillaise de Crédit'},
            'Q2003171': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Vijaya Bank'},
            'Q4349236': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Ålandsbanken'},
            'Q28705400': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'А-Банк'},
            'Q1997334': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Беларусбанк'},
            'Q1924338': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Газпромбанк'},
            'Q4340839': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Ощадбанк'},
            'Q1515015': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'ПриватБанк'},
            'Q4378147': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Приднестровский Сбербанк'},
            'Q649100': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Промсвязьбанк'},
            'Q4389243': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Райффайзен Банк Аваль'},
            'Q3920226': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Россельхозбанк'},
            'Q4132947': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'AmBank'},
            'Q610817': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco do Brasil'},
            'Q4855972': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank Simpanan Nasional'},
            'Q806678': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank of Cyprus'},
            'Q806689': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Bank of Ireland'},
            'Q2882897': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banque Dupuy de Parseval'},
            'Q590952': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Crédit Agricole'},
            'Q579747': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'GT Bank'},
            'Q7420065': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Santander'},
            'Q7978891': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Webster Bank'},
            'Q4114952': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Возрождение'},
            'Q24930461': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Почта Банк'},
            'Q16912944': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'РНКБ'},
            'Q6579041': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'ธนาคารออมสน'},
            'Q11390660': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'きらぼし銀行'},
            'Q4207208': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '上海商業儲蓄銀行'},
            'Q986744': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '中国邮政储蓄银行'},
            'Q746428': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '愛知銀行'},
            'Q333101': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '日本銀行'},
            'Q496606': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '국민은행'},
            'Q15283673': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '농협'},
            'Q484047': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '하나은행'},
            'Q1182932': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Degussa'},
            'Q2883410': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'BNA'},
            'Q2883376': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco Nación'},
            'Q2883376': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banco de la Nación'},
            'Q666694': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'CIBC'},
            'Q706533': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': '臺灣銀行'},
            #'Q806950': {'prefix': 'brand:', 'expected_tags': {'amenity': 'bank'}, 'name': 'Banque de France'}, # some are quite tricky

            'Q971649': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Orlen'},
            'Q154950': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Shell'},
            'Q7072824': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Opet'},
            'Q3335043': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Naftal'},
            'Q3240764': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Shell'},
            'Q1273376': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Station Service E. Leclerc'},
            'Q2498318': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Cosmo'},
            'Q2789310': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'OKQ8'},
            'Q12072939': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'WOG'},
            'Q66480830': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'uSmile 昆仑好'},
            'Q1615684': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Hess'},
            'Q1776022': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Statoil'},
            'Q680776': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Сургутнефтегаз'},
            'Q830621': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'H-E-B Fuel'},
            'Q3548078': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Ultramar'},
            'Q152057': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'BP'},
            'Q2741455': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'PSO'},
            'Q3088656': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Mobil'},
            'Q1634762': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Q8'},
            'Q1208279': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Petro-Canada'},
            'Q153417': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Kroger'},
            'Q2216770': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': '出光'},
            'Q458363': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Marathon'},
            'Q5936320': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Wawa'},
            'Q1640290': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'エネオス'},
            'Q565734': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Aral'},
            'Q1283291': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Valero'},
            'Q4781944': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Exxon'},
            'Q319642': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Chevron'},
            'Q549181': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'MOL'},
            'Q2836957': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Couche-Tard'},
            'Q300147': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Avia'},
            'Q329347': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Лукойл'},
            'Q168238': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'ОМВ'},
            'Q7271953': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'QuikTrip'},
            'Q1342538': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Oxxo'},
            'Q304769': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Arco'},
            'Q154037': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Total Access'},
            'Q221692': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Petronas'},
            'Q7824764': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Topaz'},
            'Q775060': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Texaco'},
            'Q168238': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Avanti'},
            'Q3088656': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'モービル'},
            'Q867662': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Esso'},
            'Q568940': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Jet'},
            'Q1640290': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'ENEOS'},
            'Q867662': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'エッソ'},
            'Q329347': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Lukoil'},
            'Q7592214': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'St1'},
            'Q4043527': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': "Mac's"},
            'Q11130894': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Benzina'},
            'Q1289348': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Indian Oil'},
            'Q11225213': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'JA-SS'},
            'Q6443340': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Kum & Go'},
            'Q922344': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Morrisons'},
            'Q1658320': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': '76'},
            'Q1656230': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Phillips 66'},
            'Q174747': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Repsol'},
            'Q854826': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Bharat Petroleum'},
            'Q677832': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Sonangol'},
            'Q1461799': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Газпромнефть'},
            'Q3302837': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Maxol'},
            'Q5373644': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'Emo'},
            'Q11528048': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': 'ゼネラル'},
            'Q277115': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fuel'}, 'name': '昭和シェル'},

            'Q11257202': {'prefix': 'brand:', 'expected_tags': {'shop': 'bicycle'}, 'name': 'サイクルベースあさひ'},

            'Q4826087': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_parts'}, 'name': 'AutoZone'},
            'Q4686051': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_parts'}, 'name': 'Advance Auto Parts'},
            'Q7071951': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_parts'}, 'name': "O'Reilly Auto Parts"},
            'Q11285915': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_parts'}, 'name': 'イエローハット'},

            'Q2099972': {'prefix': 'brand:', 'expected_tags': {'shop': 'tyres'}, 'name': 'Pneuhage'},
            'Q1129847': {'prefix': 'brand:', 'expected_tags': {'shop': 'tyres'}, 'name': 'Cooper Tire & Rubber Company'},

            'Q1035997': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Carglass'},
            'Q53268': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Toyota'},
            'Q6686': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Renault'},
            'Q3070922': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Feu Vert'},
            'Q6499202': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Sears Auto Center'},
            'Q234021': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Bosch Car Service'},
            'Q6746': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Citroën'},
            'Q620875': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Goodyear'},
            'Q784721': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'A.T.U'},
            'Q3060668': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Euromaster'},
            'Q79239635': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'F1 Autocentre'},
            'Q10580079': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Mekonomen'},
            'Q3312613': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Midas'},
            'Q3317698': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Norauto'},
            'Q3492969': {'prefix': 'brand:', 'expected_tags': {'shop': 'car_repair'}, 'name': 'Speedy'},
            
            'Q40993': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'Porsche'},
            'Q5037190': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'CarMax'},
            'Q20165': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'Nissan'},
            'Q9584': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'Honda'},
            'Q44294': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'Ford'},
            'Q9584': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'ホンダ'},
            'Q181642': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'Suzuki'},
            'Q26921': {'prefix': 'brand:', 'expected_tags': {'shop': 'car'}, 'name': 'Alfa Romeo'},

            'Q791136': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_rental'}, 'name': 'Avis'},
            'Q1543874': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_rental'}, 'name': 'Hertz'},
            'Q11123021': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_rental'}, 'name': 'オリックスレンタカー'},
            'Q11321580': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_rental'}, 'name': 'トヨタレンタカー'},
            'Q11086533': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_rental'}, 'name': 'ニッポンレンタカー'},
            'Q11086838': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_rental'}, 'name': '日産レンタカー'},

           'Q1069924': {'prefix': 'brand:', 'expected_tags': {'amenity': 'car_sharing'}, 'name': 'Zipcar'},

            'Q215657': {'prefix': 'brand:', 'expected_tags': {'shop': 'motorcycle'}, 'name': 'KTM'},

            'Q2463547': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vehicle_inspection'}, 'name': 'TÜV Nord'},
            'Q632391': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vehicle_inspection'}, 'name': 'TÜV Rheinland'},
            
            'Q10508136': {'prefix': 'brand:', 'expected_tags': {'shop': 'agrarian'}, 'name': 'Granngården'},

            'Q22059070': {'prefix': 'brand:', 'expected_tags': {'shop': 'country_store'}, 'name': 'Bomgaars'},
            'Q6859973': {'prefix': 'brand:', 'expected_tags': {'shop': 'country_store'}, 'name': 'Fleet Farm'},

            'Q459965': {'prefix': 'brand:', 'expected_tags': {'shop': 'trade'}, 'name': 'Caterpillar'},

            'Q815787': {'prefix': 'brand:', 'expected_tags': {'shop': 'garden_centre'}, 'name': 'Bellaflora'},
            'Q1183029': {'prefix': 'brand:', 'expected_tags': {'shop': 'garden_centre'}, 'name': 'Dehner'},
            'Q2927176': {'prefix': 'brand:', 'expected_tags': {'shop': 'garden_centre'}, 'name': 'Intratuin'},
            'Q3162640': {'prefix': 'brand:', 'expected_tags': {'shop': 'garden_centre'}, 'name': 'Truffaut'},
            'Q2911642': {'prefix': 'brand:', 'expected_tags': {'shop': 'garden_centre'}, 'name': 'Botanic'},

            'Q3187152': {'prefix': 'brand:', 'expected_tags': {'shop': 'toys'}, 'name': 'JouéClub'},
            'Q3197009': {'prefix': 'brand:', 'expected_tags': {'shop': 'toys'}, 'name': 'King Jouet'},
            'Q3209556': {'prefix': 'brand:', 'expected_tags': {'shop': 'toys'}, 'name': 'La Grande Récré'},
            'Q16663879': {'prefix': 'brand:', 'expected_tags': {'shop': 'toys'}, 'name': 'Maxi Toys'},
            'Q16643324': {'prefix': 'brand:', 'expected_tags': {'shop': 'toys'}, 'name': 'Детский мир'},
            'Q3382507': {'prefix': 'brand:', 'expected_tags': {'shop': 'toys'}, 'name': 'PicWic'},

            'Q5038192': {'prefix': 'brand:', 'expected_tags': {'shop': 'gift'}, 'name': 'Card Factory'},
            'Q5134299': {'prefix': 'brand:', 'expected_tags': {'shop': 'gift'}, 'name': 'Clintons'},

            'Q886177': {'prefix': 'brand:', 'expected_tags': {'shop': 'florist'}, 'name': 'Blumen Risse'},

            'Q1799875': {'prefix': 'brand:', 'expected_tags': {'shop': 'bookmaker'}, 'name': 'Ladbrokes'},
            'Q4053147': {'prefix': 'brand:', 'expected_tags': {'shop': 'bookmaker'}, 'name': 'William Hill'},
            
            'Q1311806': {'prefix': 'brand:', 'expected_tags': {'shop': 'lottery'}, 'name': 'Loterías y Apuestas del Estado'},
            
            'Q1849187': {'prefix': 'brand:', 'expected_tags': {'shop': 'alcohol'}, 'name': 'Alko'},
            'Q13639185': {'prefix': 'brand:', 'expected_tags': {'shop': 'alcohol'}, 'name': 'Gall & Gall'},
            'Q3340012': {'prefix': 'brand:', 'expected_tags': {'shop': 'alcohol'}, 'name': 'Nicolas'},
            'Q24933790': {'prefix': 'brand:', 'expected_tags': {'shop': 'alcohol'}, 'name': 'Красное & Белое'},

            'Q20639040': {'prefix': 'brand:', 'expected_tags': {'shop': 'tobacco'}, 'name': 'Nemzeti Dohánybolt'},

            'Q3382454': {'prefix': 'brand:', 'expected_tags': {'shop': 'frozen_food'}, 'name': 'Picard'},
            'Q3524695': {'prefix': 'brand:', 'expected_tags': {'shop': 'frozen_food'}, 'name': 'Thiriet'},

            'Q2176149': {'prefix': 'brand:', 'expected_tags': {'shop': 'newsagent'}, 'name': 'Primera'},

            'Q244457': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Subway'},
            'Q752941': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Taco Bell'},
            'Q465751': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Chipotle Mexican Grill'},
            'Q1043486': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Carl\'s Jr.'},
            'Q550258': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Wendy\'s'},
            'Q839466': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Domino\'s Pizza'},
            'Q1689380': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Jimmy John\'s'},
            'Q491516': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Chick-fil-A'},
            'Q175106': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Tim Hortons'},
            'Q38076': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'McDonald\'s'},
            'Q7561808': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Sonic Drive-In'},
            'Q1141226': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Dairy Queen'},
            'Q1538507': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Jack in the Box'},
            'Q524757': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'KFC'},
            'Q1205312': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'In-N-Out Burger'},
            'Q4998570': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Burgerville'},
            'Q1358690': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Panda Express'},
            'Q1204169': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'モスバーガー', 'allowed_tags': {'name:en': 'MOS BURGER', 'name:ja': 'モスバーガー', 'name:ja_rm': 'Mosu Bāgā'}},
            'Q286494': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Quick'},
            'Q1131810': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Five Guys'},
            'Q2699863': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Telepizza'},
            'Q942741': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Pollo Campero'},
            'Q5349788': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Einstein Bros. Bagels'},
            'Q11292632': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'オリジン弁当'},
            'Q17061332': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Smashburger'},
            'Q1192805': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Krispy Kreme'},
            'Q1244034': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'White Castle'},
            'Q4241838': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Крошка Картошка'},
            'Q7163311': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Penn Station'},
            'Q7132349': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Papa Murphy's"},
            'Q6445491': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'くら寿司'},
            'Q847743': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Dunkin' Donuts"},
            'Q6005623': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Imo's Pizza"},
            'Q7234777': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Potbelly'},
            'Q848773': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': '松屋'},
            'Q2353849': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'El Pollo Loco'},
            'Q6137375': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'すき家'},
            'Q17220385': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'はま寿司'},
            'Q7605233': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Steak 'n Shake"},
            'Q1183818': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Del Taco'},
            'Q7376154': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Rubio's"},
            'Q2759586': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Папа Джонс'},
            'Q2759586': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Papa John's"},
            'Q65079407': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Debonairs Pizza'},
            'Q5096235': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Chicken Express'},
            'Q1092539': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Cinnabon'},
            'Q1065819': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'ミスタードーナツ'},
            'Q630866': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Arby's"},
            'Q1585088': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Hardee's"},
            'Q5986105': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'CoCo壱番屋'},
            'Q11414722': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': '富士そば'},
            'Q28494040': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "O'Tacos"},
            'Q7845817': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Tropical Smoothie Cafe'},
            'Q10850949': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'ほっともっと'},
            'Q1393809': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Little Caesars'},
            'Q1363885': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Qdoba'},
            'Q6512823': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Lee's Sandwiches"},
            'Q17111672': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Panago'},
            'Q1535221': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Long John Silver's"},
            'Q7757289': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Pita Pit'},
            'Q11257037': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'スシロー'},
            'Q8025339': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Wingstop'},
            'Q5893363': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Honey Baked Ham'},
            'Q1089932': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Church's Chicken"},
            'Q1276832': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Hesburger'},
            'Q1143589': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Culver's"},
            'Q1143589': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Good Times'},
            'Q3403981': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Greggs'},
            'Q7285144': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': "Raising Cane's"},
            'Q6094914': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'itsu'},
            'Q582245': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Febo'},
            'Q1912172': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Max'},
            'Q7722411': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'The Chicken Rice Shop'},
            'Q7444079': {'prefix': 'brand:', 'expected_tags': {'amenity': 'fast_food'}, 'name': 'Secret Recipe'},

            'Q1189695': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Denny\'s'},
            'Q1185675': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'IHOP'},
            'Q621532': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': "Applebee's"},
            'Q23016666': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Blaze Pizza'},
            'Q4941599': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Bonefish Grill'},
            'Q509255': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Buffalo Wild Wings'},
            'Q5017108': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Cafe Rio'},
            'Q5017261': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Café Rouge'},
            'Q2438391': {'prefix': 'brand:', 'expected_tags': {'leisure': 'amusement_arcade'}, 'name': "Chuck E. Cheese's"},
            'Q1240741': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Donatos Pizza'},
            'Q5563393': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': "Giordano's Pizzeria"},
            'Q23019759': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Guzman y Gomez'},
            'Q918151': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Hard Rock Cafe'},
            'Q7801833': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Tijuana Flats'},
            'Q1025921': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Hooters'},
            'Q17020829': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': "McAlister's Deli"},
            'Q3472954': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': "Nando's"},
            'Q7071703': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': "O'Charley's"},
            'Q3045312': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Olive Garden'},
            'Q3389502': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Pizza Delight'},
            'Q7316076': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Poivre Rouge'},
            'Q846301': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Red Lobster'},
            'Q7755384': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'The Original Pancake House'},
            'Q7811777': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Toby Carvery'},
            'Q7930659': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Village Inn'},
            'Q21189156': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Yard House'},
            'Q1016072': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'Pepper Lunch'},
            'Q11276815': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'びっくりドンキー'},
            'Q11301951': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'ココス'},
            'Q11310517': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'ジョイフル'},
            'Q11310628': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'ジョナサン'},
            'Q7334856': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'リンガーハット'},
            'Q11120884': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': 'ロイヤルホスト'},
            'Q11417251': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': '和幸'},
            'Q11253593': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': '夢庵'},
            'Q11518589': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': '木曽路'},
            'Q11620063': {'prefix': 'brand:', 'expected_tags': {'amenity': 'restaurant'}, 'name': '華屋与兵衛'},

            'Q11620063': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pub'}, 'name': '華屋与兵衛'},

            'Q5880870': {'prefix': 'brand:', 'expected_tags': {'shop': 'health_food'}, 'name': 'Holland & Barrett'},

            'Q4808595': {'prefix': 'brand:', 'expected_tags': {'shop': 'nutrition_supplements'}, 'name': 'GNC'},

            'Q7130852': {'prefix': 'brand:', 'expected_tags': {}, 'name': 'Panera Bread'},
            'Q191615': {'prefix': 'brand:', 'expected_tags': {'cuisine': 'pizza'}, 'name': 'Pizza Hut'},

            'Q1591889': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Walgreens'},
            'Q2078880': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'CVS'},
            'Q3433273': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Rite Aid'},
            'Q20015002': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Farmahorro'},
            'Q7974785': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Watsons'},
            'Q6123139': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Boots'},
            'Q5856071': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Cruz Verde'},
            'Q5308184': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Drogaria São Paulo'},
            'Q15857801': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Gintarinė vaistinė'},
            'Q13646560': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Mannings'},
            'Q65684234': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'MedPlus'},
            'Q1820137': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Pharmaprix'},
            'Q1820137': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Shoppers Drug Mart'},
            'Q7643261': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Superdrug'},
            'Q4394431': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'Ригла'},
            'Q11288687': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'ウエルシア薬局'},
            'Q11301948': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'ココカラファイン'},
            'Q11304804': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'サツドラ'},
            'Q11305867': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'サンドラッグ'},
            'Q11316754': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'ダイコクドラッグ'},
            'Q11318826': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'ツルハドラッグ'},
            'Q7820097': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'トモズ'},
            'Q8014776': {'prefix': 'brand:', 'expected_tags': {'amenity': 'pharmacy'}, 'name': 'マツモトキヨシ'},
            # local mapper disagrees, hibernated for now
            #'Q477222': {'prefix': 'brand:', 'expected_tags': {'shop': 'hearing_aids'}, 'name': 'Amplifon'},

            'Q2553262': {'prefix': 'brand:', 'expected_tags': {'healthcare': 'counselling'}, 'name': 'Planned Parenthood'},

            'Q579524': {'prefix': 'brand:', 'expected_tags': {'shop': 'erotic'}, 'name': 'Ann Summers'},

            'Q10846977': {'prefix': 'brand:', 'expected_tags': {'leisure': 'adult_gaming_centre'}, 'name': 'ダイナム'},
            'Q11295831': {'prefix': 'brand:', 'expected_tags': {'leisure': 'adult_gaming_centre'}, 'name': 'ガイア'},
            'Q1905948': {'prefix': 'brand:', 'expected_tags': {'leisure': 'adult_gaming_centre'}, 'name': 'マルハン'},

            'Q5598967': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'Great Clips'},
            'Q5452622': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'First Choice Haircutters'},
            'Q1465159': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'Klier'},
            'Q5434222': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'Fantastic Sams'},
            'Q7579310': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'Sport Clips'},
            'Q1737304': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'Klipp'},
            'Q11297528': {'prefix': 'brand:', 'expected_tags': {'shop': 'hairdresser'}, 'name': 'QBハウス'},

            'Q4824602': {'prefix': 'brand:', 'expected_tags': {'healthcare': 'blood_donation'}, 'name': 'Australian Red Cross Blood Service'},
            'Q470110': {'prefix': 'brand:', 'expected_tags': {'healthcare': 'blood_donation'}, 'name': 'American Red Cross'},

            'Q4944037': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Boots Opticians'},
            'Q2000610': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Specsavers'},
            'Q618940': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Apollo-Optik'},
            'Q2829511': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Alain Afflelou'},
            'Q457822': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Fielmann'},
            'Q3354445': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Optic 2000'},
            'Q3354448': {'prefix': 'brand:', 'expected_tags': {'shop': 'optician'}, 'name': 'Optical Center'},

            'Q17035733': {'prefix': 'brand:', 'expected_tags': {'shop': 'outdoor'}, 'name': 'Trespass'},
            
            'Q509349': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Decathlon'},
            'Q4904902': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Big 5 Sporting Goods'},
            'Q6108019': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'JD Sports'},
            'Q262394': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Sport 2000'},
            'Q18485899': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Sport Zone'},
            'Q6133465': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Sprinter'},
            'Q4993863': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Stadium'},
            'Q3895': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Adidas'},
            'Q12010840': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'XXL'},
            'Q4438176': {'prefix': 'brand:', 'expected_tags': {'shop': 'sports'}, 'name': 'Спортмастер'},
            
            'Q7090329': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}},
            'Q1075788': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}},
            'Q2717882': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Holiday Inn'},
            'Q5964551': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Première Classe'},
            'Q5890701': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Homewood Suites'},
            'Q5032010': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Candlewood Suites'},
            'Q1502859': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Ramada'},
            'Q5880423': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Holiday Inn Express & Suites'},
            'Q5646230': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Hampton'},
            'Q2746220': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Crowne Plaza'},
            'Q1162859': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Hilton Garden Inn'},
            'Q794939': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'B&B Hôtel'},
            'Q830334': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Best Western'},
            'Q830334': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Best Western Plus'},
            'Q830334': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Best Western Premier'},
            'Q5254663': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Delta Hotels'},
            'Q598884': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Hilton'},
            'Q920166': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Ibis'},
            'Q1067636': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'JW Marriott'},
            'Q1709809': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Mercure'},
            'Q420545': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Novotel'},
            'Q25047720': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'Red Lion Hotels'},
            'Q1969162': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'The Westin'},
            'Q11284497': {'prefix': 'brand:', 'expected_tags': {'tourism': 'hotel'}, 'name': 'アパホテル'},

            'Q2188884': {'prefix': 'brand:', 'expected_tags': {'tourism': 'motel'}, 'name': 'Motel 6'},

            'Q13610282': {'prefix': 'brand:', 'expected_tags': {'shop': 'wholesale'}, 'name': 'Metro'},

            'Q5600598': {'prefix': 'operator:', 'expected_tags': {}},

            'Q8034539': {'prefix': 'operator:', 'expected_tags': {'office': 'government', 'name': 'WorkSafeBC'}},

            'Q3083531': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Groupama'},
            'Q1151671': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'DAK'},
            'Q17183481': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Grange Insurance'},
            'Q808361': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Barmer'},
            'Q3331021': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Macif'},
            'Q4200631': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Ингосстрах'},
            'Q4386516': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'РЕСО-Гарантия'},
            'Q4426689': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Согласие'},
            'Q2645636': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Allstate'},
            'Q160054': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'AXA'},
            'Q544532': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Mapfre'},
            'Q3331046': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'MMA'},
            'Q4397745': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Росгосстрах'},
            'Q487292': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Allianz'},
            'Q1181452': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Debeka'},
            'Q3299185': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Matmut'},
            'Q2007336': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'State Farm'},
            'Q5869232': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Fremap'},
            'Q3127528': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Harmonie Mutuelle'},
            'Q6120481': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Santa Lucía'},
            'Q1412465': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'Württembergische'},
            'Q174081': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': '明治安田生命'},
            #weird school case
            #'Q835141': {'prefix': 'brand:', 'expected_tags': {'office': 'insurance'}, 'name': 'AOK'},

            'Q5343830': {'prefix': 'brand:', 'expected_tags': {'office': 'financial_advisor'}, 'name': 'Edward Jones'},

            'Q1054480': {'prefix': 'brand:', 'expected_tags': {'office': 'estate_agent'}, 'name': 'Century 21'},
            'Q1435638': {'prefix': 'brand:', 'expected_tags': {'office': 'estate_agent'}, 'name': 'Foncia'},
            'Q3356080': {'prefix': 'brand:', 'expected_tags': {'office': 'estate_agent'}, 'name': 'Orpi'},
            'Q965845': {'prefix': 'brand:', 'expected_tags': {'office': 'estate_agent'}, 'name': 'RE/MAX'},
            'Q738853': {'prefix': 'brand:', 'expected_tags': {'office': 'estate_agent'}, 'name': 'Coldwell Banker'},
            
            'Q8901192': {'prefix': 'brand:', 'expected_tags': {'office': 'employment_agency'}, 'name': 'Pôle Emploi'},
            'Q353494': {'prefix': 'brand:', 'expected_tags': {'office': 'employment_agency'}, 'name': 'Adecco'},
            'Q1472539': {'prefix': 'brand:', 'expected_tags': {'office': 'employment_agency'}, 'name': 'Manpower'},
            'Q267840': {'prefix': 'brand:', 'expected_tags': {'office': 'employment_agency'}, 'name': 'Randstad'},
            
            'Q493751': {'prefix': 'brand:', 'expected_tags': {'office': 'consulting'}, 'name': 'KPMG'},
            'Q488048': {'prefix': 'brand:', 'expected_tags': {'office': 'consulting'}, 'name': 'PwC'},
            
            'Q19995004': {'prefix': 'brand:', 'expected_tags': {'office': 'coworking'}, 'name': 'WeWork'},

            'Q5627799': {'prefix': 'brand:', 'expected_tags': {'office': 'tax_advisor'}, 'name': 'H&R Block'},
            'Q205150': {'prefix': 'brand:', 'expected_tags': {'office': 'political_party'}, 'name': 'Front National'},

            'Q16974764': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'Amazon Locker'},
            'Q16974764': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'Amazonロッカー'},
            'Q65681213': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'Blue Rhino'},
            'Q1766703': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine', 'vending': 'parcel_pickup;parcel_mail_in'}, 'name': 'DHL Packstation'},
            'Q3182097': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine', 'vending': 'parcel_pickup;parcel_mail_in'}, 'name': 'Paczkomat InPost'},
            'Q898568': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'JT'},
            'Q2365235': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'Ozon Box'},
            'Q1185060': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'UCC'},
            'Q60989429': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'だし道楽'},
            'Q492747': {'prefix': 'brand:', 'expected_tags': {'amenity': 'vending_machine'}, 'name': 'ドール'},

            'Q24933714': {'prefix': 'brand:', 'expected_tags': {'shop': 'outpost'}, 'name': 'Wildberries'},

            'Q2989971': {'prefix': 'former_operator:', 'expected_tags': {'abandoned:man_made': 'mineshaft'}},
            'Q2989977': {'prefix': 'former_operator:', 'expected_tags': {'abandoned:man_made': 'mineshaft'}},

            'Q140957': {'prefix': 'species:', 'expected_tags': {'species': 'Dipterocarpus alatus', 'natural': 'tree', 'leaf_cycle': 'evergreen', 'leaf_type': 'broadleaved'}},
            'Q2601238': {'prefix': 'species:', 'expected_tags': {'species': 'Carya ovata', 'natural': 'tree', 'leaf_cycle': 'deciduous', 'leaf_type': 'broadleaved'}},
            'Q957447': {'prefix': 'species:', 'expected_tags': {'species': 'Polyalthia longifolia', 'natural': 'tree', 'leaf_cycle': 'evergreen', 'leaf_type': 'broadleaved'}},
            'Q157756': {'prefix': 'species:', 'expected_tags': {'species': 'Hibiscus syriacus', 'natural': 'tree', 'leaf_cycle': 'deciduous', 'leaf_type': 'broadleaved'}},
            'Q163981': {'prefix': 'species:', 'expected_tags': {'species': 'Tilia americana', 'natural': 'tree', 'leaf_cycle': 'deciduous', 'leaf_type': 'broadleaved'}},
            'Q2710065': {'prefix': 'species:', 'expected_tags': {'species': 'Embothrium coccineum', 'natural': 'tree', 'leaf_cycle': 'deciduous', 'leaf_type': 'broadleaved'}},
            'Q714180': {'prefix': 'species:', 'expected_tags': {'species': 'Ficus microcarpa', 'natural': 'tree', 'leaf_cycle': 'evergreen', 'leaf_type': 'broadleaved'}},
            'Q161105': {'prefix': 'species:', 'expected_tags': {'species': 'Platanus orientalis', 'natural': 'tree', 'leaf_cycle': 'deciduous', 'leaf_type': 'broadleaved'}},

            'Q7378': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q7368': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q327028': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q26838': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q131567': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q185038': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q142985': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q172923': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q249024': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q2293037': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q685772': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q322159': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q200339': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q818254': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q244179': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q190294': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q159857': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q2934': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q7378': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q79803': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q121439': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q58903': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q787': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25882': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q255503': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q242851': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25348': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q780': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q848706': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q780': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q149017': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q42569': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q726': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q79794': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q69581': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q34706': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q35694': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25432': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q14334': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q42699': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25384': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q165974': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q170177': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25769': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q190516': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q191781': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q179863': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q232906': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q27452479': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q80174': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q199427': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q177856': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q26423': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q131564': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q220248': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q4388': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q33609': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q7966': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q40994': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q285648': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q137528': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q775569': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q132922': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q767508': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q124410': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q741524': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q36341': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q130933': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q1061964': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q280590': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q640161': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q628239': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q41960': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q182573': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q869140': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q80952': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25438': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q148628': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q61865': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q516612': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q2169710': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25402': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q184751': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q41181': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q168976': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q643101': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q3736439': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q179225': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q189868': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q41050': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q82738': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q187024': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q269896': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q39624': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q17592': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q93208': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q1988192': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q654370': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q58697': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q18498': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q23390': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q81091': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q35517': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q192710': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q23121': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q133189': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q181191': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q29995': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q129059': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q155878': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q205930': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q26685': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q26913': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q184004': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q623466': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q729713': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q26147': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q193469': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q192967': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q19939': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q993274': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q902896': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q25894': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q34718': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q27366': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q677014': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q848656': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q859200': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q187927': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q219035': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q1004741': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q191737': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q3887135': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q1763595': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q652151': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q858264': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q21755': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q216441': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q1469688': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q168327': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q194313': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q220213': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q486745': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q314363': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q202241': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q5452918': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q26547': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q212669': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q134015': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q208043': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q185385': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q11338316': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q189484': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q188657': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q476930': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q834329': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q19707': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q188828': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q232558': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q187704': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q2305786': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q2605752': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q856009': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q902876': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q224151': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q838924': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q81056': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q824974': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
            'Q200724': {'prefix': 'species:', 'expected_tags': {'attraction': 'animal'}},
        }

    def get_problem_based_on_wikidata_blacklist(self, wikidata_id, present_wikidata_id, link):
        if wikidata_id == None:
            wikidata_id = present_wikidata_id

        try:
            prefix = self.wikidata_connection_blacklist()[wikidata_id]['prefix']
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
            potential_article_name = wikimedia_connection.get_interwiki_article_name_by_id(wikidata_id, potential_language_code, self.forced_refresh)
            if potential_article_name != None:
                return potential_language_code + ':' + potential_article_name
        return None

    def report_failed_wikipedia_page_link(self, language_code, article_name, wikidata_id):
        message = "Wikipedia article linked from OSM object using wikipedia tag is missing. Typically article was moved and wikipedia tag should be edited to point to the new one. Sometimes article was deleted and no longer exists so wikipedia tag should be deleted."
        proposed_new_target = self.get_best_interwiki_link_by_id(wikidata_id)
        if proposed_new_target != None:
            message += " wikidata tag present on element points to an existing article"
        return ErrorReport(
                    error_id = "wikipedia tag links to 404",
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
            message = "Wikidata claims that this object no longer exists. Historical, no longer existing object must not be mapped in OSM - so it means that either Wikidata is mistaken or wikipedia/wikidata tag is wrong or OSM has an outdated object." + " " + self.wikidata_data_quality_warning()
            return ErrorReport(
                            error_id = "no longer existing object",
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

    def normalized_id(self, links, wikidata_id):
        normalized_link_form = wikidata_id #may be None
        for link in links:
            if link == None:
                return None
            id_from_link = wikimedia_connection.get_wikidata_object_id_from_link(link, self.forced_refresh)
            if normalized_link_form == None:
                normalized_link_form = id_from_link
            if normalized_link_form != id_from_link:
                return None
        return normalized_link_form

    def convert_old_style_wikipedia_tags(self, wikipedia_type_keys, tags):
        links = self.wikipedia_candidates_based_on_old_style_wikipedia_keys(tags, wikipedia_type_keys)

        if tags.get('wikipedia') != None:
            links.append(tags.get('wikipedia'))

        prerequisite = {}
        prerequisite['wikidata'] = tags.get('wikidata')
        prerequisite['wikipedia'] = tags.get('wikipedia')
        for key in wikipedia_type_keys:
            prerequisite[key] = tags.get(key)

        normalized = self.normalized_id(links, tags.get('wikidata'))
        if normalized == None:
            return ErrorReport(
                error_id = "wikipedia tag in outdated form and there is mismatch between links",
                error_message = "wikipedia tag in outdated form (" + str(wikipedia_type_keys) + "). Mismatch between different links happened and requires human judgment to solve.",
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

    def get_wikipedia_from_wikidata_assume_no_old_style_wikipedia_tags(self, present_wikidata_id):
        location = (None, None)
        description = "object with wikidata=" + present_wikidata_id
        problem_indicated_by_wikidata = self.get_problem_based_on_wikidata(present_wikidata_id, description, location)
        if problem_indicated_by_wikidata:
            return problem_indicated_by_wikidata

        link = self.get_best_interwiki_link_by_id(present_wikidata_id)
        if link == None:
            return None
        language_code = wikimedia_connection.get_language_code_from_link(link)
        if language_code in self.languages_ordered_by_preference:
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
            language_code = wikimedia_connection.get_text_after_first_colon(key)
            article_name = tags.get(key)

            wikidata_id = wikimedia_connection.get_wikidata_object_id_from_article(language_code, article_name)
            if wikidata_id == None:
                links.append(language_code + ":" + article_name)
                continue

            link = self.get_best_interwiki_link_by_id(wikidata_id)
            if link == None:
                links.append(language_code + ":" + article_name)
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
        message = base_message + ", because wikidata tag points to a redirect that should be followed (" + self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article) +")"
        maybe_redirected_wikidata_id = self.get_wikidata_id_after_redirect(present_wikidata_id)
        if maybe_redirected_wikidata_id != present_wikidata_id:
            if maybe_redirected_wikidata_id == wikidata_id_from_article:
                return ErrorReport(
                    error_id = "wikipedia wikidata mismatch - follow wikidata redirect",
                    error_message = message,
                    prerequisite = {'wikidata': present_wikidata_id, 'wikipedia': language_code+":"+article_name},
                    )

        title_after_possible_redirects = self.get_article_name_after_redirect(language_code, article_name)
        is_article_redirected = (article_name != title_after_possible_redirects and article_name.find("#") == -1)
        if is_article_redirected:
            wikidata_id_from_redirect = wikimedia_connection.get_wikidata_object_id_from_article(language_code, title_after_possible_redirects, self.forced_refresh)
            if present_wikidata_id == wikidata_id_from_redirect:
                message = (base_message + ", because wikipedia tag points to a redirect that should be followed (" +
                          self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article) +")")
                message += " article redirects from " + language_code + ":" + article_name + " to " + language_code + ":" + title_after_possible_redirects
                new_wikipedia_link = language_code+":"+title_after_possible_redirects
                return ErrorReport(
                    error_id = "wikipedia wikidata mismatch - follow wikipedia redirect",
                    error_message = message,
                    desired_wikipedia_target = new_wikipedia_link,
                    prerequisite = {'wikidata': present_wikidata_id, 'wikipedia': language_code+":"+article_name},
                    proposed_tagging_changes = [{"from": {"wikipedia": language_code+":"+article_name}, "to": {"wikipedia": new_wikipedia_link}}],
                    )
        message = (base_message + " (" +
                   self.compare_wikidata_ids(present_wikidata_id, wikidata_id_from_article) +
                   " wikidata from article)")
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
        (see https://wiki.openstreetmap.org/wiki/Key:wikipedia#Secondary_Wikipedia_links ) \n\
        in case of change remember to remove wikidata tag if it is present \n\
        object categorised by Wikidata - wrong classification may be caused by wrong data on Wikidata"
        return message

    def get_should_use_subject_error(self, type, special_prefix, wikidata_id):
        return ErrorReport(
            error_id = "should use a secondary wikipedia tag",
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

    def get_error_report_if_secondary_wikipedia_tag_should_be_used(self, wikidata_id):
        # contains ideas based partially on constraints in https://www.wikidata.org/wiki/Property:P625
        class_error = self.get_error_report_if_type_unlinkable_as_primary(wikidata_id)
        if class_error != None:
            return class_error

        property_error = self.get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary(wikidata_id)
        if property_error != None:
            return property_error

    def get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary(self, wikidata_id):
        if wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P247') != None:
            return self.get_should_use_subject_error('a spacecraft', 'name:', wikidata_id)
        if wikimedia_connection.get_property_from_wikidata(wikidata_id, 'P279') != None:
            return self.get_should_use_subject_error('an uncoordinable generic object', 'name:', wikidata_id)

    def get_error_report_if_type_unlinkable_as_primary(self, wikidata_id):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id):
            potential_failure = self.get_reason_why_type_makes_object_invalid_primary_link(type_id)
            if potential_failure != None:
                return self.get_should_use_subject_error(potential_failure['what'], potential_failure['replacement'], wikidata_id)
        return None

    def get_reason_why_type_makes_object_invalid_primary_link(self, type_id):
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
        if type_id == 'Q29048322':
            return {'what': ' vehicle model', 'replacement': 'subject:'}
        if type_id == 'Q21502408':
            return {'what': 'a mandatory constraint', 'replacement': None}
        return None

    def get_error_report_if_wikipedia_target_is_of_unusable_type(self, location, wikidata_id):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id):
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

    def get_problem_based_on_wikidata_and_osm_element(self, object_description, location, wikidata_id):
        if wikidata_id == None:
            # instance data not present in wikidata
            # not fixable easily as imports from OSM to Wikidata are against rules
            # as OSM data is protected by ODBL, and Wikidata is on CC0 license
            # also, this problem is easy to find on Wikidata itself so it is not useful to report it
            return None

        return self.get_problem_based_on_wikidata(wikidata_id, object_description, location)

    def get_problem_based_on_wikidata(self, wikidata_id, description, location):
        return self.get_problem_based_on_base_types(wikidata_id, description, location)

    def get_problem_based_on_base_types(self, wikidata_id, description, location):
        base_type_ids = wikidata_processing.get_wikidata_type_ids_of_entry(wikidata_id)
        if base_type_ids == None:
            return None

        base_type_problem = self.get_problem_based_on_wikidata_base_types(location, wikidata_id)
        if base_type_problem != None:
            return base_type_problem

        if self.additional_debug:
            # TODO, IDEA - run with this parameter enable to start catching more issues
            self.complain_in_stdout_if_wikidata_entry_not_of_known_safe_type(wikidata_id, description)


    def get_problem_based_on_wikidata_base_types(self, location, wikidata_id):
        unusable_wikipedia_article = self.get_error_report_if_wikipedia_target_is_of_unusable_type(location, wikidata_id)
        if unusable_wikipedia_article != None:
            return unusable_wikipedia_article

        secondary_tag_error = self.get_error_report_if_secondary_wikipedia_tag_should_be_used(wikidata_id)
        if secondary_tag_error != None:
            return secondary_tag_error

        if location != None:
            secondary_tag_error = self.headquaters_location_indicate_invalid_connection(location, wikidata_id)
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
        if headquarters_location_data == None:
            return None
        for option in headquarters_location_data:
            location_from_wikidata = self.get_location_of_this_headquaters(option)
            if location_from_wikidata != (None, None):
                if geopy.distance.vincenty(location, location_from_wikidata).km > 20:
                    return self.get_should_use_subject_error('a company that is not linkable from a single location', 'brand:', wikidata_id)

        return None

    def complain_in_stdout_if_wikidata_entry_not_of_known_safe_type(self, wikidata_id, description_of_source):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id):
            if self.is_wikidata_type_id_recognised_as_OK(type_id):
                return None
        self.dump_base_types_of_object_in_stdout(wikidata_id, description_of_source)

    def output_debug_about_wikidata_item(self, wikidata_id):
        print("**********************")
        print(wikidata_processing.get_wikidata_type_ids_of_entry(wikidata_id))
        print(wikidata_processing.get_all_types_describing_wikidata_object(wikidata_id))
        self.complain_in_stdout_if_wikidata_entry_not_of_known_safe_type(wikidata_id, "tests")
        self.dump_base_types_of_object_in_stdout(wikidata_id, "tests")

    def dump_base_types_of_object_in_stdout(self, wikidata_id, description_of_source):
        print("----------------")
        print(wikidata_id)
        types = wikidata_processing.get_wikidata_type_ids_of_entry(wikidata_id)
        if types == None:
            print("this entry has no types")
        for type_id in types:
            print("------")
            print(description_of_source)
            print("type " + type_id)
            self.describe_unexpected_wikidata_type(type_id)

    def callback_reporting_banned_categories(self, category_id):
        ban_reson = self.get_reason_why_type_makes_object_invalid_primary_link(category_id)
        if ban_reson != None:
            return "banned as it is " + ban_reson['what'] + " !!!!!!!!!!!!!!!!!!!!!!!!!!"
        return ""

    def describe_unexpected_wikidata_type(self, type_id):
        # print entire inheritance set
        too_abstract = wikidata_processing.wikidata_entries_for_abstract_or_very_broad_concepts()
        show_debug = True
        callback = self.callback_reporting_banned_categories
        parent_categories = wikidata_processing.get_recursive_all_subclass_of(type_id, too_abstract, show_debug, callback)
        #for parent_category in parent_categories:
        #    print("if type_id == '" + parent_category + "':")
        #    print(wikidata_processing.wikidata_description(parent_category))

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
        if language_code == "pl":
            return ['Q36']
        if language_code == "de":
            return ['Q183']
        if language_code == "cz":
            return ['Q213']
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
