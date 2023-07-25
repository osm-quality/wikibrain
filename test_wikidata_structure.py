import unittest
from wikibrain import wikimedia_link_issue_reporter
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import osm_handling_config.global_config as osm_handling_config
import wikimedia_connection.wikidata_processing as wikidata_processing

class WikidataTests(unittest.TestCase):
    def detector(self):
        return wikimedia_link_issue_reporter.WikimediaLinkIssueDetector()

    def assert_passing_all_tests(self, wikidata, wikipedia):
        tags = {'wikidata': wikidata, 'wikipedia': wikipedia}
        location = (0, 0)
        object_type = "node"
        object_description = "test"
        report = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if report != None:
            print(report.data())
        self.assertEqual(None, report)

    def assert_failing_full_tests(self, wikidata, wikipedia):
        tags = {'wikidata': wikidata, 'wikipedia': wikipedia}
        location = (0, 0)
        object_type = "node"
        object_description = "test"
        report = self.detector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if report != None:
            print(report.data())
        self.assertNotEqual(None, report)

    def is_unlinkable_check(self, type_id):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        return self.detector().get_error_report_if_type_unlinkable_as_primary(type_id, {'wikipedia': 'dummy'})
        # get_error_report_if_type_unlinkable_as_primary
        #return self.detector().get_error_report_if_secondary_wikipedia_tag_should_be_used(type_id, {'wikipedia': 'dummy'})
    
    def is_not_an_event(self, type_id):
        self.is_not_a_specific_error_class(type_id, 'an event')

    def is_not_a_behavior(self, type_id):
        self.is_not_a_specific_error_class(type_id, 'a behavior')
        self.is_not_a_specific_error_class(type_id, 'a human behavior')

    def is_not_a_specific_error_class(self, type_id, expected_error_class):
        potential_failure = self.detector().get_error_report_if_type_unlinkable_as_primary(type_id, {'wikidata': type_id})
        if potential_failure == None:
            return
        if potential_failure.data()['error_id'] == 'should use a secondary wikipedia tag - linking from wikidata tag to ' + expected_error_class:
            self.dump_debug_into_stdout(type_id, "is_not_a_specific_error_class failed")
            self.assertNotEqual(potential_failure.data()['error_id'], 'should use a secondary wikipedia tag - linking from wikidata tag to ' + expected_error_class)

    def dump_debug_into_stdout(self, type_id, why):
        print()
        print()
        print()
        print("dump_debug_into_stdout", why)
        self.dump_debug_about_specific_type_id_into_stdout(type_id)
        parent_categories = wikidata_processing.get_recursive_all_subclass_of(type_id, self.detector().ignored_entries_in_wikidata_ontology(), False, callback=None)
        for subclass in parent_categories:
            if type_id == subclass:
                continue
            print(type_id, "is also subclassed with", subclass)
            if subclass in wikimedia_link_issue_reporter.WikimediaLinkIssueDetector.ignored_entries_in_wikidata_ontology():
                print("but it is in wikimedia_link_issue_reporter.WikimediaLinkIssueDetector.ignored_entries_in_wikidata_ontology()")
            else:
                self.dump_debug_about_specific_type_id_into_stdout(subclass)

    def dump_debug_about_specific_type_id_into_stdout(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        reported = ""
        reported += "\n"
        reported += "\n"
        reported += "https://www.wikidata.org/wiki/" + type_id + "\n"
        reported += "https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Ontology\n"
        reported += "\n"
        if is_unlinkable != None:
            invalid_groups = self.detector().invalid_types()
            reported_already = [] # sometimes the same problem name has multiple invalid types pointing to it
            # in such case it should be still reported once
            for key in invalid_groups:
                possible_match = invalid_groups[key]["what"]
                if "is about " + possible_match + ", so it is very unlikely to be correct" in is_unlinkable.error_message:
                    if possible_match not in reported_already:
                        reported += "== {{Q|" + type_id + "}} is " + possible_match + ", according to Wikidata ontology =="
                        reported_already.append(possible_match)
            if reported_already == []:
                reported += "weird, no group matched"
                reported += is_unlinkable.error_message
            reported += "\n"
        else:
            pass
        print(reported)
        self.detector().dump_base_types_of_object_in_stdout(type_id, 'tests')
        print()

    def assert_linkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable != None:
            self.dump_debug_into_stdout(type_id, "assert_linkability failed")
        self.assertEqual(None, is_unlinkable)

    def assert_unlinkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable == None:
            self.dump_debug_into_stdout(type_id, "assert_unlinkability failed")
        self.assertNotEqual(None, is_unlinkable)

    def test_rejects_links_to_events(self):
        self.assert_unlinkability('Q134301')

    def test_rejects_links_to_events_case_of_hinderburg_disaster(self):
        self.assert_unlinkability('Q3182723')

    def test_rejects_links_to_events_case_of_a_battle(self):
        self.assert_unlinkability('Q663435')

    def test_rejects_links_to_spacecraft(self):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        self.assertNotEqual(None, self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q2513', "wikipedia"))

    def test_reject_links_to_humans(self):
        self.assert_unlinkability('Q561127')

    def test_reject_links_to_term_shopping(self):
        # https://www.openstreetmap.org/way/452123938
        self.assert_unlinkability('Q830036')

    def test_detecting_makro_as_invalid_primary_link(self):
        self.assert_unlinkability('Q704606')

    def test_detecting_tesco_as_invalid_primary_link(self):
        self.assert_unlinkability('Q487494')

    def test_detecting_carrefour_as_invalid_primary_link(self):
        self.assert_unlinkability('Q217599')

    def test_detecting_genus_of_plants_as_invalid_primary_link(self):
        self.assert_unlinkability('Q4262384')

    def test_detecting_genus_aircraft_family_as_invalid_primary_link(self):
        self.assert_unlinkability('Q890188')

    def test_detecting_cropp_as_invalid_primary_link(self):
        self.assert_unlinkability('Q9196793')

    def test_detecting_crash_as_invalid_primary_link(self):
        self.assert_unlinkability('Q1801568')

    def test_detecting_castle_as_valid_primary_link(self):
        self.assert_linkability('Q2106892')

    def test_detecting_castle__that_was_used_as_prison_as_valid_primary_link(self):
        self.assert_linkability('Q11913101')

    def test_detecting_reconstructed_castle_as_valid_primary_link(self):
        self.assert_linkability('Q2461065')

    def test_detecting_reconstructed_gate_as_valid_primary_link(self):
        self.assert_linkability('Q30035365')

    def test_detecting_fort_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q20089971')

    def test_detecting_fort_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q865131')

    def test_detecting_footbridge_as_valid_primary_link(self):
        self.assert_linkability('Q109717267')

    def test_detecting_fort_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q11962228')

    def test_detecting_roundabout_art_as_valid_primary_link(self):
        self.assert_linkability('Q105414527')

    def test_detecting_funicular_as_valid_primary_link(self):
        self.assert_linkability('Q5614426')

    def test_detecting_fast_tram_as_valid_primary_link(self):
        self.assert_linkability('Q1814872')

    def test_detecting_summer_school_as_valid_primary_link(self):
        self.assert_linkability('Q5150387')

    def test_detecting_high_school_as_valid_primary_link(self):
        self.assert_linkability('Q9296000')

    def test_walk_of_fame_as_valid_primary_link(self):
        self.assert_linkability('Q2345775')

    def test_detecting_high_school_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q85652366')

    def test_detecting_primary_school_as_valid_primary_link(self):
        self.assert_linkability('Q7112654')

    def test_detecting_fountain_as_valid_primary_link(self):
        self.assert_linkability('Q992764')

    def test_detecting_wastewater_plant_as_valid_primary_link(self):
        self.assert_linkability('Q11795812')

    def test_detecting_burough_as_valid_primary_link(self):
        self.assert_linkability('Q1630')

    def test_detecting_expressway_as_valid_primary_link(self):
        self.assert_linkability('Q5055176') # not an event

    def test_detecting_university_as_valid_primary_link(self):
        self.assert_linkability('Q1887879') # not a website (as "open access publisher" is using website, but is not a website)

    def test_detecting_university_as_valid_primary_link(self):
        self.assert_linkability('Q1887879') # not an event (via "education")

    def test_train_line_as_valid_primary_link(self):
        self.assert_linkability('Q3720557') # train service is not a service (Q15141321) defined as "transcation..."

    def test_narrow_gauge_train_line_as_valid_primary_link(self):
        self.assert_linkability('Q1642426')

    def test_train_category_as_invalid_primary_link(self):
        self.assert_unlinkability('Q680235')

    def test_tide_organ_as_valid_primary_link(self):
        self.assert_linkability('Q7975291') # art is not sublass of creativity - though it is using creativity. It is also not sublass of a process.

    def test_specific_event_center_as_valid_primary_link(self):
        self.assert_linkability('Q7414066')

    def test_park_as_valid_primary_link(self):
        self.assert_linkability('Q1535460') # cultural heritage ( https://www.wikidata.org/w/index.php?title=Q210272&action=history ) is not a subclass of heritage designation, heritage (https://www.wikidata.org/w/index.php?title=Q2434238&offset=&limit=500&action=history) is not subclass of preservation
        
    def test_another_park_as_valid_primary_link(self):
        self.assert_linkability('Q60331605')

    def test_litography_workshop_as_valid_primary_link(self):
        self.assert_linkability('Q7680903')

    def test_geoglyph_as_valid_primary_link(self):
        self.assert_linkability('Q7717476') # not an event - via Q12060132 ("hillside letter" that is not a signage, it is product of a signage)

    def test_dunes_as_valid_primary_link(self):
        self.assert_linkability('Q1130721') # not an event - aeolian landform (Q4687862) is not sublass of aeolian process, natural object is not sublass of natural phenonemon ( https://www.wikidata.org/w/index.php?title=Q29651224&action=history )

    def test_tree_taxon_as_invalid_primary_link_testcase_a(self):
        self.assert_unlinkability('Q2453469')

    def test_specific_tree_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q6703503') # not an event

    def test_specific_tree_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q33040885') # not a taxon

    def test_specific_tree_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q15133783')

    def test_specific_tree_as_valid_primary_link_testcase_d(self):
        self.assert_linkability('Q995630')

    def test_sheltered_information_board_as_valid_primary_link(self):
        self.assert_linkability('Q7075518') # not an event

    def test_wind_farm_as_valid_primary_link(self):
        self.assert_linkability('Q4102067') # not an event

    def test_farm_as_valid_primary_link(self):
        self.assert_linkability('Q99902190')

    def test_hollywood_sign_as_valid_primary_link(self):
        self.assert_linkability('Q180376') # not an event (hollywood sign is not an instance of signage)

    def test_railway_segment_as_valid_primary_link(self):
        self.assert_linkability('Q2581240') # not a physical process

    def test_another_railway_segment_as_valid_primary_link(self):
        self.assert_linkability('Q1126676') # not a physical process

    def test_railway_miniature_as_valid_primary_link(self):
        self.assert_linkability('Q685524')

    def test_railway_station_as_valid_primary_link(self):
        self.assert_linkability('Q2016811')

    def test_railway_line_as_valid_primary_link(self):
        self.assert_linkability('Q706198')

    def test_country_as_valid_primary_link(self):
        self.assert_linkability('Q30') # not an event

    def test_aqueduct_as_valid_primary_link(self):
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=prev&oldid=1674919371
        self.assert_linkability('Q2859225') # not an event

    def test_public_housing_as_valid_primary_link(self):
        self.assert_linkability('Q22329573') # not an event - aeolian landform (Q4687862) is not sublass of aeolian process

    def test_dry_lake_as_valid_primary_link(self):
        self.assert_linkability('Q1780699') # not an event

    def test_industrial_property_as_valid_primary_link(self):
        self.assert_linkability('Q5001422') # not an event

    def test_cemetery_as_valid_primary_link(self):
        self.assert_linkability('Q30593659') # not an event

    def test_cholera_cemetery_as_valid_primary_link(self):
        self.assert_linkability('Q18147583')

    def test_megaproject_as_valid_primary_link(self):
        self.assert_linkability('Q782093') # some megaprojects are already existing, project ( https://www.wikidata.org/wiki/Q170584 ) may be already complete

    def test_pilgrim_route_as_valid_primary_link(self):
        self.assert_linkability('Q829469')

    def test_totem_pole_as_valid_primary_link(self):
        self.assert_linkability('Q104536355')
 
    def test_botanical_garden_as_valid_primary_link(self):
        self.assert_linkability('Q589884')
        self.assert_linkability('Q677516')
       
    def test_alley_as_valid_primary_link(self):
        self.assert_linkability('Q3413299')

    def test_zoo_as_valid_primary_link(self):
        self.assert_linkability('Q1886334')

    def test_public_aquarium_as_valid_primary_link(self):
        self.assert_linkability('Q4782760')

    def test_grave_as_valid_primary_link(self):
        self.assert_linkability('Q11789060')

    def test_monument_as_valid_primary_link(self):
        self.assert_linkability('Q11823211')

    def test_holocaust_memorial_monument_as_valid_primary_link(self):
        self.assert_linkability('Q570442')

    def test_galvanoplastified_memorial_as_valid_primary_link(self):
        self.assert_linkability('Q1419054')

    def test_cafe_as_valid_primary_link(self):
        self.assert_linkability('Q672804')

    def test_religious_administrative_area_as_valid_primary_link(self):
        self.assert_linkability('Q1364786')

    def test_administrative_area_as_valid_primary_link_testcase_1(self):
        self.assert_linkability('Q1144105')

    def test_administrative_area_as_valid_primary_link_testcase_2(self):
        self.assert_linkability('Q266657')

    def test_hiking_trail_as_valid_primary_link(self):
        self.assert_linkability('Q783074')

    def test_peak_as_valid_primary_link(self):
        self.assert_linkability('Q31792598')

    def test_urban_park_as_valid_primary_link(self):
        self.assert_linkability('Q98411615')

    def test_protected_landscape_area_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q8465509')

    def test_protected_landscape_area_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q6901264')

    def test_headquarters_landscape_area_as_valid_primary_link(self):
        self.assert_linkability('Q5578587')

    def test_museum_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q731126')

    def test_museum_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q27490233')

    def test_museum_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q9337658')

    def test_museum_as_valid_primary_link_testcase_with_mission_site(self):
        self.assert_linkability('Q3316762')

    def test_mural_as_valid_primary_link_testcase1(self):
        self.assert_linkability('Q20103040')

    def test_mural_as_valid_primary_link_testcase2(self):
        self.assert_linkability('Q29351056')

    def test_mural_as_valid_primary_link_testcase3(self):
        self.assert_linkability('Q94279877')

    def test_sgraffito_mural_as_valid_primary_link(self):
        self.assert_linkability('Q63149011')

    def test_ceramic_mural_as_valid_primary_link(self):
        self.assert_linkability('Q75320653')

    def test_trademark_as_valid_primary_link(self):
        # trademark added to ignored_entries_in_wikidata_ontology to solve this
        self.assert_linkability('Q1392479') # everything can be trademarked, even hamlet and it does not make it an event

    def test_community_garden_as_valid_primary_link(self):
        self.assert_linkability('Q49493599')

    def test_people_mover_as_valid_primary_link(self):
        self.assert_linkability('Q2908764')

    def test_wind_turbine_as_valid_primary_link(self):
        self.assert_linkability('Q2583657')

    def test_cathedral_as_valid_primary_link(self):
        # see https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=1358272534&oldid=1358269822
        self.assert_linkability('Q2064095')

    def test_sign_as_valid_primary_link_testcase_a(self):
        # see https://www.wikidata.org/w/index.php?title=Wikidata%3AProject_chat&type=revision&diff=1358269822&oldid=1358263283
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=prev&oldid=1359638515
        self.assert_linkability('Q4804421')

    def test_sign_as_valid_primary_link_testcase_b(self):
        # physical sign vs signage again
        self.assert_linkability('Q41284513')

    def test_neon_sign_as_valid_primary_link(self):
        # see link in test_sign_as_valid_primary_link for related discussion about physical signs
        self.assert_linkability('Q11694423')

    def test_milestone_as_valid_primary_link(self):
        # see link in test_sign_as_valid_primary_link for related discussion about physical signs
        self.assert_linkability('Q83545869')

    def test_maria_column_as_valid_primary_link(self):
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&oldid=1359739358#How_to_prevent_Maria_column_from_being_classified_as_a_process?
        self.assert_linkability('Q3894014')

    def test_wayside_cross_as_valid_primary_link(self):
        # see test_maria_column_as_valid_primary_link for a discussion link
        self.assert_linkability('Q63895140')

    def test_submarine_cable_as_valid_primary_link(self):
        # see test_maria_column_as_valid_primary_link for a discussion link
        self.assert_linkability('Q7197229')

    def test_statue_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q87720384')

    def test_statue_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q60314102')

    def test_statue_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q115610737')

    def test_collosal_statue_as_valid_primary_link(self):
        self.assert_linkability('Q805442')

    def test_world_war_one_statue_as_valid_primary_link(self):
        self.assert_linkability('Q113621082')

    def test_equestrian_statue_as_valid_primary_link(self):
        self.assert_linkability('Q17570718')

    def test_some_outdoor_art_as_valid_primary_link(self):
        self.assert_linkability('Q106274335')

    def test_air_force_academy_as_valid_primary_link(self):
        self.assert_linkability('Q2015914')

    def test_pipeline_as_valid_primary_link(self):
        self.assert_linkability('Q7700085')

    def test_submarine_cable_as_valid_primary_link(self):
        self.assert_linkability('Q7118902')

    def test_country_club_as_valid_primary_link(self):
        self.assert_linkability('Q2669978')

    def test_tennis_court_as_valid_primary_link(self):
        self.assert_linkability('Q52454')

    def test_house_later_housing_area_as_valid_primary_link(self):
        self.assert_linkability('Q6906313')

    def test_artwork_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q57838673')

    def test_artwork_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q115930654')

    def test_gate_as_valid_primary_link(self):
        self.assert_linkability('Q26317425')

    def test_cricket_club_as_valid_primary_link(self):
        self.assert_linkability('Q3195284')

    def test_meridian_as_valid_primary_link(self):
        self.assert_linkability('Q131108')

    def test_place_where_conspiracy_theory_happened_as_valid_primary_link(self):
        # borderline as article actually focuses more on a conspiracy theory itself...
        self.assert_linkability('Q7535626')

    def test_sculpture_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q105492941')

    def test_sculpture_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q108428976')

    def test_sculpture_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q108410880')

    def test_animal_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q108421050')

    def test_subway_station_as_valid_primary_link(self):
        self.assert_linkability('Q89406786')

    def test_administrative_boundary_as_valid_primary_link(self):
        self.assert_linkability('Q912777')

    def test_hybrid_lift_as_valid_primary_link(self):
        self.assert_linkability('Q1331434')

    def test_castle_as_valid_primary_link(self):
        self.assert_linkability('Q5734420')

    def test_chapel_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q4993989')

    def test_chapel_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q29784970')

    def test_specific_locomotive_as_valid_primary_link(self):
        self.assert_linkability('Q28673829')

    def test_specific_prototype_as_valid_primary_link(self):
        self.assert_linkability('Q701696')

    def test_tram_yard_as_valid_primary_link(self):
        self.assert_linkability('Q9346796')

    def test_existing_section_of_proposed_motorway_as_valid_primary_link(self):
        # https://www.openstreetmap.org/way/414708185#map=16/52.0582/21.4617
        self.assert_linkability('Q68683422')

    def test_sign_as_valid_primary_link(self):
        self.assert_linkability('Q6800883')

    def test_chubby_male_child_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q5475472') # not an event

    def test_geyser_as_valid_primary_link(self):
        self.assert_linkability('Q1129264') # not an event

    def test_specific_ship_as_valid_primary_link(self):
        # https://www.wikidata.org/wiki/Wikidata:Project_chat#USS_Niagara_museum_ship_is_classified_as_%22group_of_humans%22
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=1674915580&oldid=1674914531
        self.assert_linkability('Q7872265') # not an event

    def test_tomb_as_valid_primary_link(self):
        self.assert_linkability('Q3531157')

    def test_rock_cut_tomb_as_valid_primary_link(self):
        # fixed in https://www.wikidata.org/w/index.php?title=Q1404229&diff=1746681007&oldid=1711659919
        # that removed "rock-cut architecture" from https://www.wikidata.org/wiki/Q1404229
        # as individual tombs are not "creation of structures, buildings, and sculptures by excavating solid rock"
        self.assert_linkability('Q5952161')

    def test_cave_church_as_valid_primary_link(self):
        self.assert_linkability('Q26263282')

    def test_wayside_shrine_as_valid_primary_link(self):
        self.assert_linkability('Q41318154')

    def test_specific_locomotive_as_valid_primary_link(self):
        self.assert_linkability('Q113278632')
        self.assert_passing_all_tests('Q113278632', 'en:Santa Fe 769')

    def test_cave_as_valid_primary_link(self):
        self.assert_linkability('Q1275277')

    def test_cliff_as_valid_primary_link(self):
        self.assert_linkability('Q924900')

    def test_company_is_not_human(self):
        for type_id in wikidata_processing.get_all_types_describing_wikidata_object("Q15832619", wikimedia_link_issue_reporter.WikimediaLinkIssueDetector.ignored_entries_in_wikidata_ontology()):
            if type_id == "Q5":
                self.assertTrue(False)

    def test_specific_animal_as_valid_primary_link(self):
        self.assert_linkability('Q7082812')

    def test_weird_biography_that_is_actually_about_house(self):
        # https://en.wikipedia.org/wiki/Edith_Macefield
        # this pretends to be about human while it is about building
        self.assert_linkability('Q5338613')

    def test_event_entry_that_is_actually_strongly_about_location(self):
        self.assert_linkability('Q5371519')

    def test_monastery_as_valid_primary_link(self):
        self.assert_linkability('Q4508631')
        self.assert_passing_all_tests('Q4508631', 'pl:Cziłter-Koba') # https://pl.wikipedia.org/wiki/Czi%C5%82ter-Koba

    def test_detecting_weapon_model_as_invalid_primary_link(self):
        # https://www.openstreetmap.org/node/3014280721
        self.assert_unlinkability('Q266837')

        # https://www.openstreetmap.org/node/1331944863
        self.assert_unlinkability('Q7277047')

    def test_detecting_mine_disaster_as_invalid_primary_link(self):
        self.assert_unlinkability('Q4558986')

    def test_open_pit_mine_as_valid_primary_link(self):
        self.assert_linkability('Q2387872')

    def test_underground_mine_as_valid_primary_link(self):
        self.assert_linkability('Q1408907')

    def test_movie_filming_location_as_valid_primary_link(self):
        self.assert_linkability('Q821784')

    def test_detecting_bombing_as_invalid_primary_link(self):
        self.assert_unlinkability('Q885225')

    def test_australian_administrative_boundary_as_valid_primary_link(self):
        # https://www.openstreetmap.org/relation/7032873
        self.assert_linkability('Q3179144')
        report = self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q3179144', "wikipedia")
        if report != None:
            self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q3179144', "wikipedia", show_debug=True)
        self.assert_passing_all_tests('Q3179144', 'en:Unincorporated Far West Region')

    def test_pilgrimage_route_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q41150')

    def test_fountain_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q822122')

    def test_modern_artwork_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q64435838')

    def test_river_source_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q47037286')

    def test_old_house_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q31147655')

    def test_ferry_route_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q926453')

    def test_another_ferry_route_as_valid_primary_link(self):
        self.assert_linkability('Q2593299')

    def test_tram_system_as_valid_primary_link(self):
        # it is not a behavior...
        self.assert_linkability('Q9360797')

    def test_drug_treatment_center_as_valid_primary_link(self):
        self.assert_linkability('Q11143416')

    def test_pastoral_lease_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q8293195')

    def test_park_and_node_beach_as_valid_primary_link(self):
        # not an event
        self.assert_linkability('Q5619268')

    def test_parish_as_valid_primary_link(self):
        # organisations are linkable
        self.assert_linkability('Q11808430')

    def test_local_bank_as_valid_primary_link(self):
        self.assert_linkability('Q9165022')

    def test_murder_as_invalid_primary_link(self):
        self.assert_unlinkability('Q4468588')

    def test_circus_as_valid_primary_link(self):
        self.assert_linkability('Q4453469')

    def test_bar_as_valid_primary_link(self):
        self.assert_linkability('Q16910525')

    def test_territory_as_valid_primary_link(self):
        self.assert_linkability('Q25842885')

    def test_island_with_territorial_dispute_as_valid_primary_link(self):
        self.assert_linkability('Q598889')

    def test_district_with_specific_history_as_valid_primary_link(self):
        self.assert_linkability('Q64124')

    def test_skyspace_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q63066124')

    def test_one_more_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q65029693')

    def test_gene_as_invalid_primary_link(self):
        self.assert_unlinkability('Q425264')

    def test_protected_kiosk_as_valid_primary_link(self):
        self.assert_linkability('Q10356475')

    def test_defunct_protected_kiosk_building_as_valid_primary_link(self):
        self.assert_linkability('Q14715519')

    def test_fishing_grounds_as_valid_primary_link(self):
        self.assert_linkability('Q5338344')

    def test_glassworks_as_valid_primary_link(self):
        self.assert_linkability('Q63124776')

    def test_specific_shop_as_valid_primary_link(self):
        self.assert_linkability('Q104698108')

    def test_specific_observation_tower_as_valid_primary_link(self):
        self.assert_linkability('Q116445748')
        self.assert_linkability('Q113115337')

    def test_landslide_as_valid_primary_link(self):
        self.assert_linkability('Q1946797')

    def test_general_article_about_cycling_in_belarus_as_invalid_primary_link(self):
        self.assert_unlinkability('Q97007609')

    def test_forest_as_valid_primary_link(self):
        self.assert_linkability('Q20713832')

    def test_retail_chain_as_invalid_primary_link(self):
        self.assert_unlinkability('Q3345688')

    def test_tank_family_as_invalid_primary_link(self):
        self.assert_unlinkability('Q172233')

    def test_tank_family_as_invalid_primary_link_testcase_b(self):
        self.assert_unlinkability('Q2720752')

    def test_federal_aid_program_as_invalid_primary_link(self):
        self.assert_unlinkability('Q7990125')

    def test_incinerator_as_valid_primary_link(self):
        # it is not a physical process...
        self.assert_linkability('Q1424213')

    def test_tourist_trail_as_valid_primary_link(self):
        self.assert_linkability('Q112876332')

    def test_old_rail_trail_as_valid_primary_link(self):
        self.assert_linkability('Q107412801')

    def test_scenic_route_as_valid_primary_link(self):
        self.assert_linkability('Q1337273')

    def test_set_of_sculptures_forming_route_as_valid_primary_link(self):
        self.assert_linkability('Q2293084')

    def test_firefighting_museum_as_valid_primary_link(self):
        self.assert_linkability('Q76629326')

    def test_specific_ritual_object_as_valid_primary_link(self):
        self.assert_linkability('Q43386863')

    def test_biosphere_reserve_as_valid_primary_link(self):
        self.assert_linkability('Q26271338')

    def test_inn_sign_as_valid_primary_link(self):
        self.assert_linkability('Q41402928')

    def test_joke_machine_as_valid_primary_link(self):
        self.assert_linkability('Q60238364')

    def test_abandoned_village_as_valid_primary_link(self):
        self.assert_linkability('Q105643919')

    def test_regular_village_as_valid_primary_link(self):
        self.assert_linkability('Q3039540')

    def test_hotel_as_valid_primary_link(self):
        self.assert_linkability('Q41411301')

    def test_business_park_as_valid_primary_link(self):
        self.assert_linkability('Q107022150')

    def test_horsecar_tourism_attraction_as_valid_primary_link(self):
        self.assert_linkability('Q9360797')

    def test_lighthouse_as_valid_primary_link(self):
        self.assert_linkability('Q28376122')

    def test_hospice_as_valid_primary_link(self):
        self.assert_linkability('Q177545')

    def test_berlin_wall_as_valid_primary_link(self):
        self.assert_linkability('Q5086')

    def test_paleontological_site_as_valid_primary_link(self):
        self.assert_linkability('Q7354875')

    def test_sewer_network_as_valid_primary_link(self):
        # a bit dubious but is not a behaviour...
        self.assert_linkability('Q1399679')

    def test_community_as_valid_primary_link(self):
        # a bit dubious but is not a behaviour...
        self.assert_linkability('Q2073041')

    def test_artist_run_space_as_valid_primary_link(self):
        self.assert_linkability('Q780609')

    def test_set_of_rocks_as_valid_primary_link(self):
        self.assert_linkability('Q878769')

    def test_chimney_as_valid_primary_link(self):
        self.assert_linkability('Q17792230')

    def test_exhibition_as_valid_primary_link(self):
        self.assert_linkability('Q63208613')

    def test_building_complex_as_valid_primary_link(self):
        self.assert_linkability('Q2319878')

    def test_palace_as_valid_primary_link(self):
        self.assert_linkability('Q11939856')

    def test_church_building_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q9333671')

    def test_church_building_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q9167695')

    def test_church_building_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q9167731')

    def test_snowpack_as_valid_primary_link(self):
        self.assert_linkability('Q11762336')

    def test_religious_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q104895379')

    def test_graduation_tower_as_valid_primary_link(self):
        self.assert_linkability('Q9363870')

    def test_reconstructed_tower_as_valid_primary_link(self):
        self.assert_linkability('Q106462927')

    def test_boulder_as_valid_primary_link(self):
        self.assert_linkability('Q664518')

    def test_globe_as_valid_primary_link(self):
        self.assert_linkability('Q5327187')

    def test_stellarator_as_valid_primary_link(self):
        self.assert_linkability('Q315738')

    def test_escape_room_as_valid_primary_link(self):
        self.assert_linkability('Q18209063')

    def test_telephone_booth_as_valid_primary_link(self):
        self.assert_linkability('Q22025014')

    def test_city_as_valid_primary_link(self):
        self.assert_linkability('Q13298')

    def test_excavation_as_valid_primary_link(self):
        self.assert_linkability('Q398648')

    def test_city_part_as_valid_primary_link(self):
        self.assert_linkability('Q73289125')

    def test_stable_as_valid_primary_link(self):
        self.assert_linkability('Q30562672')

    def test_cowshed_as_valid_primary_link(self):
        self.assert_linkability('Q30555460')

    def test_specific_theatre_as_valid_primary_link(self):
        self.assert_linkability('Q7671545')

    def test_specific_institution_as_valid_primary_link(self):
        self.assert_linkability('Q11713051')

    def test_coastal_defense_fort_as_valid_primary_link(self):
        self.assert_linkability('Q5472138')

    def test_coastal_defense_fort_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q22084285')

    def test_railing_as_valid_primary_link(self):
        self.assert_linkability('Q37818361')

    def test_monastery_with_peat_bath_as_valid_primary_link(self):
        self.assert_linkability('Q27914521')

    def test_green_belt_as_valid_primary_link(self):
        self.assert_linkability('Q883390')

    def test_cross_dyke_as_valid_primary_link(self):
        self.assert_linkability('Q883390')

    def test_power_line_as_valid_primary_link(self):
        self.assert_linkability('Q1563634')

    def test_swimming_pool_complex_as_valid_primary_link(self):
        self.assert_linkability('Q2216235')

    def test_hot_swimming_pool_complex_as_valid_primary_link(self):
        self.assert_linkability('Q118384823')

    def test_power_cable_as_valid_primary_link(self):
        self.assert_linkability('Q314180')

    def test_power_station_as_valid_primary_link(self):
        self.assert_linkability('Q19378684')

    def test_power_station_with_cogeneration_as_valid_primary_link(self):
        self.assert_linkability('Q106674849')
        self.assert_linkability('Q4295189')
        self.assert_linkability('Q60583697')

    def test_ranch_as_valid_primary_link(self):
        self.assert_linkability('Q7185999')

    def test_mall_as_valid_primary_link(self):
        self.assert_linkability('Q9265538')

    def test_wall_as_valid_primary_link(self):
        self.assert_linkability('Q1543119')

    def test_clonal_colony_as_valid_primary_link(self):
        self.assert_linkability('Q921090')

    def test_horse_pond_as_valid_primary_link(self):
        self.assert_linkability('Q49473780')

    def test_office_building_as_valid_primary_link(self):
        self.assert_linkability('Q1590873')

    def test_station_of_a_cross_as_valid_primary_link(self):
        self.assert_linkability('Q98488381')

    def test_garden_as_valid_primary_link(self):
        self.assert_linkability('Q19575149')

    def test_that_defunct_monastery_is_not_an_event(self):
        self.is_not_an_event('Q28976876')

    def test_that_bmw_ad_buildings_is_valid_primary_link(self):
        self.assert_linkability('Q699614')

    def test_that_university_organisation_is_not_an_event(self):
        self.is_not_an_event('Q106592334')

    def test_that_defunct_school_is_not_an_event(self):
        self.is_not_an_event('Q113019862')


    def test_that_propaganda_institution_is_not_a_mental_process(self):
        self.is_not_a_specific_error_class('Q157033', 'a mental process')

    def test_that_radar_network_is_not_a_mental_process(self):
        self.is_not_a_specific_error_class('Q378431', 'a mental process')

    def test_that_business_is_not_a_social_issue(self):
        self.is_not_a_specific_error_class('Q110699468', 'a social issue')

    def test_that_data_protection_institution_is_not_a_profession(self):
        self.is_not_a_specific_error_class('Q55499784', 'a profession')

    def test_that_russian_war_company_is_not_a_profession_but_is_unlinkable_anyway(self):
        self.is_not_a_specific_error_class('Q188508', 'a profession')
        #self.assert_unlinkability('Q188508') TODO

    def test_that_flight_school_is_not_a_human_activity(self):
        self.is_not_a_specific_error_class('Q4654871', 'a human activity')

    def test_that_company_is_not_an_economic_sector_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q1655072') TODO
        self.is_not_a_specific_error_class('Q1655072', 'an economic sector')

    def test_that_company_is_not_an_economic_sector_but_is_unlinkable_anyway_testcase_b(self):
        #self.assert_unlinkability('Q552581') TODO
        self.is_not_a_specific_error_class('Q552581', 'an economic sector')

    def test_that_company_is_not_an_economic_sector_but_is_unlinkable_anyway_testcase_c(self):
        #self.assert_unlinkability('Q173941') TODO
        self.is_not_a_specific_error_class('Q173941', 'an economic sector')

    def test_that_mountain_rescue_organization_is_not_an_economic_sector_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q306066')
        self.is_not_a_specific_error_class('Q4654871', 'an economic sector')

    def test_that_mural_is_not_a_academic_discipline(self):
        self.is_not_a_specific_error_class('Q219423', 'an academic discipline')

    def test_that_drug_rehabilitation_community_is_not_an_event(self):
        self.is_not_an_event('Q2219871')

    def test_that_diet_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q3132857')
        self.is_not_an_event('Q3132857')

    def test_that_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q37156') # IBM
        self.is_not_an_event('Q37156')
        self.is_not_a_behavior('Q37156')

    def test_that_postal_delivery_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q1093368')
        self.is_not_an_event('Q1093368')
        self.is_not_a_behavior('Q1093368')        

    def test_that_company_making_events_is_not_an_event(self):
        self.is_not_an_event('Q3093234')        
        self.is_not_a_behavior('Q3093234')
        # TODO - it is not a valid link either

    def test_that_software_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q468381') # Avira
        self.is_not_an_event('Q468381')
        self.is_not_a_behavior('Q468381')

    def test_that_software_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q468381')
        self.is_not_an_event('Q468381')
        self.is_not_a_behavior('Q468381')

    def test_that_another_company_is_not_an_event_or_behavior(self):
        self.is_not_an_event('Q3211063')
        self.is_not_a_behavior('Q3211063')
        # TODO - it is not a valid link either

    def test_that_yet_another_company_is_not_an_event_or_behavior(self):
        # https://www.wikidata.org/wiki/Q1285495
        self.is_not_an_event('Q1285495')
        self.is_not_a_behavior('Q1285495')
        # TODO - it is not a valid link either

    def test_that_wifi_making_initiative_is_not_an_event_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q2363543') TODO
        self.is_not_an_event('Q2363543')
        self.is_not_a_behavior('Q2363543')

    def test_that_event_is_unlinkable(self):
        self.assert_unlinkability('Q4380984')

    def test_that_university_or_its_department_is_linkable(self):
        self.assert_linkability('Q16902376')

    def test_that_animal_breeding_location_is_linkable(self):
        self.assert_linkability('Q50810212')

    def test_that_software_is_not_an_event(self):
        self.is_not_an_event('Q25874683')

    def test_that_australian_administrative_area_is_valid_link(self):
        self.assert_linkability('Q1533526')
        self.assert_linkability('Q947334')
        self.assert_linkability('Q1030580')
        self.assert_linkability('Q1847617')
        self.assert_linkability('Q353997')
        self.assert_linkability('Q1016835')
        self.assert_linkability('Q1624414')
        self.assert_linkability('Q912566')
        self.assert_linkability('Q1338860')
        self.assert_linkability('Q1742110')
        
    def test_that_building_group_is_valid_link(self):
        self.assert_linkability('Q16886821')

    def test_that_specific_waterfront_development_is_valid_link(self):
        self.assert_linkability('Q5363395')

    def test_that_wine_region_is_valid_link(self):
        self.assert_linkability('Q24521756') # though winde region itself seems unmappable in OSM...

    def test_that_charity_organization_is_not_an_event_or_behavior(self):
        self.is_not_an_event('Q7075332')
        self.is_not_a_behavior('Q7075332')

    def test_that_married_couple_an_event_or_behavior(self):
        self.is_not_an_event('Q3051246')
        self.is_not_a_behavior('Q3051246')

    def test_that_organisation_is_not_an_event(self):
        self.is_not_an_event('Q15852617')

    def test_that_comic_strip_is_not_an_event_or_behavior(self):
        self.is_not_an_event('Q1129715')
        self.is_not_a_behavior('Q1129715')

    def test_that_gabon_is_not_an_event_or_behavior(self):
        self.is_not_an_event('Q1000')
        self.is_not_a_behavior('Q1000')

    def test_that_community_center_is_not_an_event_or_behavior_and_likely_is_valid_link(self):
        self.is_not_an_event('Q102043581')
        self.is_not_a_behavior('Q102043581')
        self.assert_linkability('Q102043581')

    def test_that_government_organisation_is_not_an_event_or_behavior(self):
        self.is_not_an_event('Q55504346')
        self.is_not_a_behavior('Q55504346')

    def test_that_business_organisation_is_not_an_event_or_behavior_testcase_a(self):
        self.is_not_an_event('Q1653655')
        self.is_not_a_behavior('Q1653655')

    def test_that_business_organisation_is_not_an_event_or_behavior_testcase_b(self):
        self.is_not_an_event('Q2328484')
        self.is_not_a_behavior('Q2328484')

    def test_that_business_organisation_is_not_an_event_or_behavior_testcase_c(self):
        self.is_not_an_event('Q135635')
        self.is_not_a_behavior('Q135635')

    def test_that_business_organisation_is_not_an_event_or_behavior_testcase_d(self):
        self.is_not_an_event('Q37156')
        self.is_not_a_behavior('Q37156')

    def test_that_business_organisation_is_not_an_event_or_behavior_testcase_e(self):
        self.is_not_an_event('Q649618')
        self.is_not_a_behavior('Q649618')

    def test_observation_network_is_not_a_behavior(self):
        self.is_not_a_behavior('Q21427321')

    def test_government_office_is_not_a_behavior(self):
        self.is_not_a_behavior('Q3882136')

    def test_government_office_also_this_one_is_not_a_behavior(self):
        self.is_not_a_behavior('Q2955976')

    def test_theme_park_as_valid_primary_link(self):
        self.assert_linkability('Q14531179')

    def test_nazi_complex_as_valid_primary_link(self):
        self.assert_linkability('Q320076')

    def test_college_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q884105')

    def test_college_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q4589150')

    def test_college_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q6514765')

    def test_specific_building_as_valid_primary_link(self):
        self.assert_linkability('Q15807394')

    def test_archeological_site_as_valid_primary_link(self):
        self.assert_linkability('Q17372554')

    def test_wetland_as_valid_primary_link(self):
        self.assert_linkability('Q53953145')

    def test_bridge_as_valid_primary_link(self):
        self.assert_linkability('Q2220859')

    def test_garden_element_as_valid_primary_link(self):
        self.assert_linkability('Q101579214')

    def test_polder_as_valid_primary_link(self):
        self.assert_linkability('Q929195')

    def test_tunnel_as_valid_primary_link(self):
        self.assert_linkability('Q927797')

    def test_pedestrian_tunnel_as_valid_primary_link(self):
        self.assert_linkability('Q2346336')

    def test_bicycle_sharing_system_is_not_human_behavior(self):
        self.is_not_a_behavior('Q3555363')

    def test_wikimedia_deutschland_is_not_human_behavior(self):
        self.is_not_a_behavior('Q8288')

    def test_ngo_as_invalid_primary_link(self):
        self.assert_unlinkability('Q2363543')

    def test_grafitti_wall_as_valid_primary_link(self):
        self.assert_linkability('Q69689708')

    def test_prehistoric_settlement_as_valid_primary_link(self):
        self.assert_linkability('Q1015819')

    def test_generic_bench_entry_as_invalid_primary_link_p279_should_be_used_as_indicator(self):
        # https://www.wikidata.org/wiki/Q204776
        # has P279
        self.assertNotEqual(None, wikimedia_connection.get_property_from_wikidata('Q204776', 'P279'))
        self.assertNotEqual(None, self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q204776', 'tag summary'))
        self.assertNotEqual(None, self.detector().get_error_report_if_secondary_wikipedia_tag_should_be_used('Q204776', {'wikidata': 'Q204776'}))
        self.assertNotEqual(None, self.detector().get_problem_based_on_wikidata_base_types(None, 'Q204776', {'wikidata': 'Q204776'}))
        self.assertNotEqual(None, self.detector().get_problem_based_on_base_types('Q204776', {'wikidata': 'Q204776'}, 'decription', None))
        self.assertNotEqual(None, self.detector().get_problem_based_on_wikidata('Q204776', {'wikidata': 'Q204776'}, 'decription', None))
        self.assertNotEqual(None, self.detector().get_problem_based_on_wikidata_and_osm_element('object_description', None, 'Q204776', {'wikidata': 'Q204776'}))
        self.assertNotEqual(None, self.detector().freely_reorderable_issue_reports('object_description', None, {'wikidata': 'Q204776'}))
        self.assert_failing_full_tests('Q204776', 'en:Bench (furniture)')

    def test_france_italy_border_as_valid_primary_link(self):
        self.assert_linkability('Q1991288')

    def test_autonomus_administrative_area_as_valid_primary_link(self):
        self.assert_linkability('Q756294')

    def test_specific_battery_as_valid_primary_link(self):
        self.assert_linkability('Q15179168')

    def test_squatted_building_as_valid_primary_link(self):
        self.assert_linkability('Q15303877')

    def test_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q215392', 'an intentional human activity')

    def test_another_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q1814208', 'an intentional human activity')
        # TODO - it is not a valid link either

    def test_municipal_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q1285495', 'an intentional human activity')
        # TODO - it is not a valid link either

    def test_ridesharing_company_is_not_a_legal_action(self):
        self.is_not_a_specific_error_class('Q692400', 'an intentional human activity')
        self.is_not_a_specific_error_class('Q692400', 'a legal action')
        # TODO - it is not a valid link either

    def test_ridesharing_network_is_not_a_legal_action(self):
        self.is_not_a_specific_error_class('Q23955689', 'an intentional human activity')
        self.is_not_a_specific_error_class('Q23955689', 'a legal action')
        self.assert_unlinkability('Q23955689')

    def test_porcelain_manufacture_is_not_an_intentional_human_activity_but_result_of_it(self):
        self.is_not_a_specific_error_class('Q895625', 'an intentional human activity')

    def test_another_site_is_not_an_intentional_human_activity_but_result_of_it(self):
        self.is_not_a_specific_error_class('Q16467716', 'an intentional human activity')

    def test_government_office_is_not_an_intentional_human_activity_but_result_of_it(self):
        self.is_not_a_specific_error_class('Q27479792', 'an intentional human activity')

    def test_deposit_system_is_not_a_research(self):
        self.is_not_a_specific_error_class('Q4077395', 'a research')

    def test_apostle_is_not_fictional_but_still_invalid(self):
        self.is_not_a_specific_error_class('Q51672', 'a fictional entity')
        tags = {"wikidata": "Q51672"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual (None, problem)
        if "fictional" in problem.data()['error_id']:
            print(problem.data()['error_id'])
            self.assertNotEqual (True, "fictional" in problem.data()['error_id'])

    def test_herod_is_not_fictional_but_still_invalid_link(self):
        self.is_not_a_specific_error_class('Q43945', 'a fictional entity')
        tags = {"wikidata": "Q43945"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual (None, problem)
        if "fictional" in problem.data()['error_id']:
            print(problem.data()['error_id'])
            self.assertNotEqual (True, "fictional" in problem.data()['error_id'])

    def test_jesus_is_not_fictional_but_still_invalid_link(self):
        # https://en.wikipedia.org/wiki/Historicity_of_Jesus
        self.is_not_a_specific_error_class('Q302', 'a fictional entity')
        tags = {"wikidata": "Q302"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual (None, problem)
        if "fictional" in problem.data()['error_id']:
            print(problem.data()['error_id'])
            self.assertNotEqual (True, "fictional" in problem.data()['error_id'])


    def test_street_with_brothels_as_valid_primary_link(self):
        self.assert_linkability('Q1877599')

    def test_promenade_as_valid_primary_link(self):
        self.assert_linkability('Q15052053')

    def test_brothel_as_valid_primary_link(self):
        self.assert_linkability('Q4745250')

    def test_cave_nature_reserve_as_valid_primary_link(self):
        self.assert_linkability('Q116396391')

    def test_rancho_as_valid_primary_link(self):
        self.assert_linkability('Q7290956')

    def test_island_rancho_as_valid_primary_link(self):
        self.assert_linkability('Q845229')

    def test_ugly_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q445256')

    def test_telescope_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q1632481')

    def test_telescope_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q1513315')

    def test_distributed_telescope_as_valid_primary_link(self):
        self.assert_linkability('Q1192324')

    def test_canopy_walkway_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q27478902')

    def test_canopy_walkway_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q64760026')

    def test_industrial_region_as_valid_primary_link(self):
        self.assert_linkability('Q7303912')

    def test_andorra_country_as_valid_primary_link(self):
        self.assert_linkability('Q228')

    def test_detect_battle_more_specifically_than_generic_event_testcase_a(self):
        self.is_not_an_event('Q4087439')

    def test_detect_battle_more_specifically_than_generic_event_testcase_b(self):
        self.is_not_an_event('Q677959')

    def test_andorra_country_as_valid_primary_link(self):
        self.assert_linkability('Q228')

    def test_school_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q4059246')

    def test_school_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q5038462')

    def test_temple_as_valid_primary_link(self):
        self.assert_linkability('Q28058072')

    def test_brewery_as_valid_primary_link(self):
        self.assert_linkability('Q11603175')

    def test_low_emission_zone_as_valid_primary_link(self):
        self.assert_linkability('Q3826967')

    def test_cottage_as_valid_primary_link(self):
        self.assert_linkability('Q109301056')

    def test_ruined_cottage_as_valid_primary_link(self):
        self.assert_linkability('Q108459640')

    def test_library_as_valid_primary_link(self):
        self.assert_linkability('Q11551945')

    def test_location_with_optical_illusion_as_valid_primary_link(self):
        self.assert_linkability('Q1325829')

    def test_location_with_optical_illusion_as_valid_primary_link(self):
        self.assert_linkability('Q1325829')

    def test_protected_scottish_bay_as_valid_primary_link(self):
        self.assert_linkability('Q1246011')

    def test_path_with_public_right_of_way_as_valid_primary_link(self):
        self.assert_linkability('Q5142648')

    def test_specific_muslim_religious_site_as_valid_primary_link(self):
        self.assert_linkability('Q5834042')

    def test_mountain_summit_as_valid_primary_link(self):
        # it was classified as summit as in "meeting of heads of state or government" :)
        self.assert_linkability('Q21010152')

    def test_business_is_not_an_academic_discipline(self):
        self.is_not_a_specific_error_class('Q13604004', 'an academic discipline')

    def test_fad_diet_is_not_an_academic_discipline(self):
        self.is_not_a_specific_error_class('Q3132857', 'an academic discipline')

    def test_dinosaur_trace_as_valid_primary_link(self):
        self.assert_linkability('Q1226704')

    def test_region_as_valid_primary_link(self):
        self.assert_linkability('Q1402033')

    def test_scammy_pseudomuseum_as_valid_primary_link(self):
        self.assert_linkability('Q19865287')

    def test_university_campus_as_valid_primary_link(self):
        self.assert_linkability('Q4066906')

    def test_building_part_as_valid_primary_link(self):
        self.assert_linkability('Q76012362')

    def test_maybe_defunct_car_cemetery_as_valid_primary_link(self):
        self.assert_linkability('Q1620927')

    def test_that_studies_center_is_not_an_event(self):
        self.is_not_an_event('Q106592334')

    def test_that_association_is_not_an_event(self):
        self.is_not_an_event('Q157033')

    def test_islamic_army_is_not_an_event(self):
        self.is_not_an_event('Q271110')

    def test_tree_or_more_specifically_clonal_colony_as_valid_primary_link(self):
        self.assert_linkability('Q19865287')

    def test_geotope_as_valid_primary_link(self):
        self.assert_linkability('Q48261221')

    def test_archeological_site_as_valid_primary_link(self):
        self.assert_linkability('Q66815081')

    def test_arty_pedestrian_bridge_as_valid_primary_link(self):
        self.assert_linkability('Q65594284')

    def test_sculpture_garden_as_valid_primary_link(self):
        self.assert_linkability('Q860863')

    def test_gorge_as_valid_primary_link(self):
        self.assert_linkability('Q1647633')

    def test_landform_as_valid_primary_link(self):
        self.assert_linkability('Q312118')

    def test_social_facility_as_valid_primary_link(self):
        self.assert_linkability('Q105564991')

    def test_icon_painting_as_valid_primary_link(self):
        self.assert_linkability('Q3918454')

    def test_religious_artwork_as_valid_primary_link(self):
        self.assert_linkability('Q23641766')

    def test_heretical_sect_is_not_a_conflict(self):
        self.is_not_a_specific_error_class('Q958306', 'a conflict')

    def test_refinery_as_valid_primary_link(self):
        self.assert_linkability('Q3417387')

    def test_archeological_remnants_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q108990211')

    def test_archeological_remnants_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q108987278')

    def test_military_base_as_valid_primary_link(self):
        self.assert_linkability('Q62092177')

    def test_fish_weir_official_recognised_as_heritage_asset_as_valid_primary_link(self):
        self.assert_linkability('Q26207149')

    def test_irrigation_system_as_valid_primary_link(self):
        self.assert_linkability('Q12074417')

    def test_artificial_waterway_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q99706580')

    def test_artificial_waterway_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q19299105')

    def test_plain_in_hungary_as_valid_primary_link(self):
        self.assert_linkability('Q1295104')

    def test_industrial_district_as_valid_primary_link(self):
        self.assert_linkability('Q6436825')

    def test_attempted_low_energy_building_as_valid_primary_link(self):
        self.assert_linkability('Q26933425')

    def test_opera_as_valid_primary_link(self):
        self.assert_linkability('Q1598188')

    def test_restaurant_as_valid_primary_link(self):
        self.assert_linkability('Q76059198')

    def test_restaurant_where_shooting_took_place_as_valid_primary_link(self):
        self.assert_linkability('Q6649212')

    def test_oil_refinery_as_valid_primary_link(self):
        self.assert_linkability('Q1260981')

    def test_mountain_with_free_flight_site_as_valid_primary_link(self):
        self.assert_linkability('Q3322275')
        self.assert_linkability('Q16631790')
        self.assert_linkability('Q3411080')
        self.assert_linkability('Q43373')

        # assumed to be also freeflight mess
        self.assert_linkability('Q3393574')
        self.assert_linkability('Q2972416')

    def test_street_lighting_structure_as_valid_primary_link(self):
        self.assert_linkability('Q37805607')

    def test_tolkien_influence_article_as_invalid_primary_link(self):
        self.assert_unlinkability('Q1237666')

    def test_cinema_of_europe_as_invalid_primary_link(self):
        self.assert_unlinkability('Q993246')

    def test_features_of_firefox_as_invalid_primary_link(self):
        self.assert_unlinkability('Q459708')

    def test_taxon_as_invalid_primary_link(self):
        self.assert_unlinkability('Q159570')
        self.assert_unlinkability('Q26899')
        self.assert_unlinkability('Q26771')
        self.assert_unlinkability('Q158746')
