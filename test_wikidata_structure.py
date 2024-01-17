import unittest
from wikibrain import wikimedia_link_issue_reporter
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import osm_handling_config.global_config as osm_handling_config
import wikimedia_connection.wikidata_processing as wikidata_processing


class WikidataTests(unittest.TestCase):
    def detector(self):
        return wikimedia_link_issue_reporter.WikimediaLinkIssueDetector()

    def assert_passing_all_tests(self, tags):
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

    def dump_debug_into_stdout(self, type_id, why, show_only_banned=True):
        print()
        print()
        print()
        print("dump_debug_into_stdout", why)
        self.dump_debug_into_stdout_internal(type_id, show_only_banned)

    def dump_debug_into_stdout_internal(self, type_id, show_only_banned):
        is_unlinkable = self.is_unlinkable_check(type_id)
        reported = ""
        reported += "\n"
        reported += "\n"
        reported += "https://www.wikidata.org/wiki/" + type_id + "\n"
        reported += "https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Ontology\n"
        reported += "\n"
        if is_unlinkable != None:
            invalid_groups = self.detector().invalid_types()
            reported_already = []  # sometimes the same problem name has multiple invalid types pointing to it
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
        self.detector().describe_unexpected_wikidata_structure(type_id, show_only_banned)
        print()

    def assert_linkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable != None:
            self.dump_debug_into_stdout(type_id, "assert_linkability failed")
        self.assertEqual(None, is_unlinkable)

    def assert_unlinkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable == None:
            self.dump_debug_into_stdout(type_id, "assert_unlinkability failed", show_only_banned=False)
        self.assertNotEqual(None, is_unlinkable)

    def brand_still_exists(self, wikidata_id, name, reference):
        status = self.detector().check_is_object_brand_is_existing({"brand:wikidata": wikidata_id})
        if status != None:
            print()
            print()
            print("== Still existing brand: " + name + " ==")
            print("https://www.wikidata.org/wiki/" + wikidata_id + " has a blanket nonexistence claim, while it could be more specific (not applying to the brand part)")
            print()
            print(reference)
        self.assertEqual(None, status)

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

    def test_detecting_fort_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q11962228')

    def test_detecting_reconstructed_fort_as_valid_primary_link(self):
        self.assert_linkability('Q2498184')

    def test_bridge_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q2220859')

    def test_bridge_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q14629016')

    def test_bridge_to_nowhere_as_valid_primary_link(self):
        self.assert_linkability('Q79049183')

    def test_detecting_footbridge_as_valid_primary_link(self):
        self.assert_linkability('Q109717267')

    def test_detecting_roundabout_art_as_valid_primary_link(self):
        self.assert_linkability('Q105414527')

    def test_detecting_funicular_as_valid_primary_link(self):
        self.assert_linkability('Q5614426')

    def test_detecting_fast_tram_network_as_invalid_primary_link(self):
        self.assert_unlinkability('Q1814872')

    def test_detecting_school_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q5060518')

    def test_detecting_school_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q828763')

    def test_detecting_summer_school_as_valid_primary_link(self):
        self.assert_linkability('Q5150387')

    def test_detecting_high_school_as_valid_primary_link(self):
        self.assert_linkability('Q9296000')

    def test_detecting_sport_school_as_valid_primary_link(self):
        self.assert_linkability('Q2677095')

    def test_walk_of_fame_as_valid_primary_link(self):
        self.assert_linkability('Q2345775')

    def test_hall_of_fame_as_valid_primary_link(self):
        self.assert_linkability('Q8027203')
        self.assert_linkability('Q1366018')
        self.assert_linkability('Q258100') # award and musem in one object        
    
    def test_plaque_as_valid_primary_link(self):
        self.assert_linkability('Q1364556')

    def test_detecting_high_school_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q85652366')

    def test_detecting_primary_school_as_valid_primary_link(self):
        self.assert_linkability('Q7112654')

    def test_detecting_fountain_as_valid_primary_link(self):
        self.assert_linkability('Q992764')
        self.assert_linkability('Q684661')

    def test_detecting_fountain_as_valid_primary_link_testcase_b(self):
        # seems to complain about https://www.wikidata.org/wiki/Q483453
        self.assert_linkability('Q104836694')
        self.assert_linkability('Q684661')
        self.assert_linkability('Q122415457')

    def test_detecting_wastewater_plant_as_valid_primary_link(self):
        self.assert_linkability('Q11795812')

    def test_detecting_waste_heap_as_valid_primary_link(self):
        self.assert_linkability('Q1526711')

    def test_detecting_burough_as_valid_primary_link(self):
        self.assert_linkability('Q1630')

    def test_detecting_expressway_as_valid_primary_link(self):
        self.assert_linkability('Q5055176')

    def test_detecting_university_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q1887879')  # not a website (as "open access publisher" is using website, but is not a website)

    def test_detecting_university_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q1887879')

    def test_detecting_university_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q178848')

    def test_train_line_as_valid_primary_link(self):
        self.assert_linkability('Q3720557')  # train service is not a service (Q15141321) defined as "transcation..."

    def test_narrow_gauge_train_line_as_valid_primary_link(self):
        self.assert_linkability('Q1642426')

    def test_train_category_as_invalid_primary_link(self):
        self.assert_unlinkability('Q680235')

    def test_tide_organ_as_valid_primary_link(self):
        self.assert_linkability('Q7975291')  # art is not sublass of creativity - though it is using creativity. It is also not sublass of a process.

    def test_specific_event_center_as_valid_primary_link(self):
        self.assert_linkability('Q7414066')

    def test_park_as_valid_primary_link(self):
        self.assert_linkability('Q1535460')  # cultural heritage ( https://www.wikidata.org/w/index.php?title=Q210272&action=history ) is not a subclass of heritage designation, heritage (https://www.wikidata.org/w/index.php?title=Q2434238&offset=&limit=500&action=history) is not subclass of preservation

    def test_another_park_as_valid_primary_link(self):
        self.assert_linkability('Q60331605')

    def test_geographic_region_as_valid_primary_link(self):
        # should not be mapped in OSM, but as long as is this is validly linked
        self.assert_linkability('Q11819931')

    def test_litography_workshop_as_valid_primary_link(self):
        self.assert_linkability('Q7680903')

    def test_geoglyph_as_valid_primary_link(self):
        self.assert_linkability('Q7717476')  # not an event - via Q12060132 ("hillside letter" that is not a signage, it is product of a signage)

    def test_dunes_as_valid_primary_link(self):
        self.assert_linkability('Q1130721')  # not an event - aeolian landform (Q4687862) is not sublass of aeolian process, natural object is not sublass of natural phenonemon ( https://www.wikidata.org/w/index.php?title=Q29651224&action=history )

    def test_tree_taxon_as_invalid_primary_link_testcase_a(self):
        self.assert_unlinkability('Q2453469')

    def test_specific_tree_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q6703503')

    def test_specific_tree_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q33040885')

    def test_specific_tree_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q15133783')

    def test_specific_tree_as_valid_primary_link_testcase_d(self):
        self.assert_linkability('Q995630')

    def test_specific_tree_as_valid_primary_link_testcase_e(self):
        self.assert_linkability('Q1958003')

    def test_sheltered_information_board_as_valid_primary_link(self):
        self.assert_linkability('Q7075518')

    def test_wind_farm_as_valid_primary_link(self):
        self.assert_linkability('Q4102067')

    def test_farm_as_valid_primary_link(self):
        self.assert_linkability('Q99902190')

    def test_hollywood_sign_as_valid_primary_link(self):
        self.assert_linkability('Q180376')  # not an event (hollywood sign is not an instance of signage)

    def test_railway_segment_as_valid_primary_link(self):
        self.assert_linkability('Q2581240')

    def test_another_railway_segment_as_valid_primary_link(self):
        self.assert_linkability('Q1126676')

    def test_railway_miniature_as_valid_primary_link(self):
        self.assert_linkability('Q685524')

    def test_railway_station_as_valid_primary_link(self):
        self.assert_linkability('Q2016811')

    def test_sinkhole_as_valid_primary_link(self):
        self.assert_linkability('Q1409355')

    def test_door_knob_as_valid_primary_link(self):
        self.assert_linkability('Q618385')

    def test_railway_line_as_valid_primary_link(self):
        self.assert_linkability('Q706198')
        self.assert_linkability('Q877800')
        self.assert_passing_all_tests({'wikidata': 'Q877800', 'wikipedia': 'de:Bahnstrecke Hochstadt-Marktzeuln–Probstzella'})

    def test_railway_line_redirect_as_valid_primary_link(self):
        # https://www.openstreetmap.org/way/436798487
        self.assert_linkability('Q802652')
        self.assert_passing_all_tests({'wikipedia': 'de:Württembergische Allgäubahn'})
        

    def test_privilidged_railway_line_as_valid_primary_link(self):
        self.assert_linkability('Q259992')

    def test_dinner_theater_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q16920269')

    def test_dinner_theater_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q19870965')

    def test_country_as_valid_primary_link(self):
        self.assert_linkability('Q30')

    def test_aqueduct_as_valid_primary_link(self):
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=prev&oldid=1674919371
        self.assert_linkability('Q2859225')

    def test_public_housing_as_valid_primary_link(self):
        self.assert_linkability('Q22329573')  # not an event - aeolian landform (Q4687862) is not sublass of aeolian process

    def test_dry_lake_as_valid_primary_link(self):
        self.assert_linkability('Q1780699')

    def test_industrial_property_as_valid_primary_link(self):
        self.assert_linkability('Q5001422')

    def test_cemetery_as_valid_primary_link(self):
        self.assert_linkability('Q30593659')

    def test_cholera_cemetery_as_valid_primary_link(self):
        self.assert_linkability('Q18147583')

    def test_megaproject_as_valid_primary_link(self):
        self.assert_linkability('Q782093')  # some megaprojects are already existing, project ( https://www.wikidata.org/wiki/Q170584 ) may be already complete

    def test_pilgrim_route_as_valid_primary_link(self):
        self.assert_linkability('Q829469')

    def test_totem_pole_as_valid_primary_link(self):
        self.assert_linkability('Q104536355')

    def test_agritourism_accomodation_as_valid_primary_link(self):
        self.assert_linkability('Q116236459')

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

    def test_grave_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q4199484')

    def test_monument_as_valid_primary_link(self):
        self.assert_linkability('Q11823211')

    def test_monument_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q11823211')
        # "plastic arts"
        self.assert_linkability('Q101608972')
        self.assert_linkability('Q110518230')
        self.assert_linkability('Q98541460')
        self.assert_linkability('Q104574569')
        self.assert_linkability('Q101440995')
        self.assert_linkability('Q102046335')
        self.assert_linkability('Q102032154')

    def test_holocaust_memorial_monument_as_valid_primary_link(self):
        self.assert_linkability('Q570442')

    def test_galvanoplastified_memorial_as_valid_primary_link(self):
        self.assert_linkability('Q1419054')

    def test_streetlight_group_as_valid_primary_link(self):
        self.assert_linkability('Q98480604')

    def test_war_memorial_monument_as_valid_primary_link(self):
        self.assert_linkability('Q72284863')

    def test_cafe_as_valid_primary_link(self):
        self.assert_linkability('Q672804')

    def test_religious_administrative_area_as_valid_primary_link(self):
        self.assert_linkability('Q1364786')

    def test_administrative_area_as_valid_primary_link_testcase_1(self):
        self.assert_linkability('Q1144105')

    def test_administrative_area_as_valid_primary_link_testcase_2(self):
        self.assert_linkability('Q266657')

    def test_japanese_administrative_area_as_valid_primary_link(self):
        self.assert_linkability('Q1207746')

    def test_hiking_trail_as_valid_primary_link(self):
        self.assert_linkability('Q783074')

    def test_hiking_trail_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q3613097')

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
        self.assert_linkability('Q27490233')
        self.assert_linkability('Q9337658')
        self.assert_linkability('Q157003')

    def test_museum_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q76632276')

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

    def test_historical_marker_as_valid_primary_link(self):
        self.assert_linkability('Q49529009')

    def test_trademark_as_valid_primary_link(self):
        # trademark added to ignored_entries_in_wikidata_ontology to solve this
        self.assert_linkability('Q1392479')  # everything can be trademarked, even hamlet, and it does not make it an event

    def test_community_garden_as_valid_primary_link(self):
        self.assert_linkability('Q49493599')

    def test_community_garden_as_valid_primary_link_tescase_b(self):
        self.assert_linkability('Q110407892')

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

    def test_nude_statue_as_valid_primary_link(self):
        self.assert_linkability('Q37878723')

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
        self.assert_linkability('Q55326744')
        self.assert_linkability('Q117317485')

    def test_some_outdoor_art_as_valid_primary_link(self):
        self.assert_linkability('Q106274335')

    def test_air_force_academy_as_valid_primary_link(self):
        self.assert_linkability('Q2015914')

    def test_pipeline_as_valid_primary_link(self):
        self.assert_linkability('Q7700085')

    def test_submarine_cable_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q7118902')

    def test_country_club_as_valid_primary_link(self):
        self.assert_linkability('Q2669978')

    def test_comedy_club_as_valid_primary_link(self):
        self.assert_linkability('Q1791352')

    def test_tennis_court_as_valid_primary_link(self):
        self.assert_linkability('Q52454')

    def test_house_later_housing_area_as_valid_primary_link(self):
        self.assert_linkability('Q6906313')

    def test_building_as_valid_primary_link(self):
        self.assert_linkability('Q118569606')

    def test_industrial_building_as_valid_primary_link(self):
        self.assert_linkability('Q118444443')

    def test_house_in_specific_style_as_valid_primary_link(self):
        self.assert_linkability('Q115691031')
        self.assert_linkability('Q121811317')

    def test_specific_garden_centre_as_valid_primary_link(self):
        # https://www.wikidata.org/w/index.php?title=Q260569&diff=2033544461&oldid=1926943045
        self.assert_linkability('Q67202863')
        self.assert_linkability('Q110538508')
        self.assert_linkability('Q7201474')

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

    def test_artillery_battery_as_valid_primary_link(self):
        # coastal artillery gets classified directly as
        # https://www.wikidata.org/wiki/Q1358324
        # lets see how it will be fixed at https://www.wikidata.org/wiki/Q121879554
        self.assert_linkability('Q121879554')
        self.assert_linkability('Q121879591')
        self.assert_linkability('Q121879557')
        self.assert_linkability('Q114736345')
        self.assert_linkability('Q121879384')
        self.assert_linkability('Q121879386')

    def test_sculpture_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q105492941')

    def test_sculpture_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q108428976')

    def test_sculpture_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q108410880')

    def test_sculpture_as_valid_primary_link_testcase_d(self):
        self.assert_linkability('Q114397796')
        self.assert_linkability('Q98541460')

    def test_animal_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q108421050')

    def test_subway_station_as_valid_primary_link(self):
        self.assert_linkability('Q89406786')
        self.assert_linkability('Q65169408')

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
        self.assert_linkability('Q5475472')

    def test_saint_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q818035')

    def test_geyser_as_valid_primary_link(self):
        self.assert_linkability('Q1129264')

    def test_specific_ship_as_valid_primary_link(self):
        # https://www.wikidata.org/wiki/Wikidata:Project_chat#USS_Niagara_museum_ship_is_classified_as_%22group_of_humans%22
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=1674915580&oldid=1674914531
        self.assert_linkability('Q7872265')

    def test_tomb_as_valid_primary_link(self):
        self.assert_linkability('Q3531157')

    def test_rock_cut_tomb_as_valid_primary_link(self):
        # fixed in https://www.wikidata.org/w/index.php?title=Q1404229&diff=1746681007&oldid=1711659919
        # that removed "rock-cut architecture" from https://www.wikidata.org/wiki/Q1404229
        # as individual tombs are not "creation of structures, buildings, and sculptures by excavating solid rock"
        self.assert_linkability('Q5952161')

    def test_cave_church_as_valid_primary_link(self):
        self.assert_linkability('Q26263282')

    def test_cave_church_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q99590884')

    def test_wayside_shrine_as_valid_primary_link(self):
        self.assert_linkability('Q41318154')

    def test_specific_locomotive_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q113278632')
        self.assert_passing_all_tests({'wikidata': 'Q113278632', 'wikipedia': 'en:Santa Fe 769'})

    def test_cave_as_valid_primary_link(self):
        self.assert_linkability('Q1275277')

    def test_cave_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q58460091')

    def test_specific_dealer_repair_shop_as_valid_primary_link(self):
        self.assert_linkability('Q76555141')

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

    def test_location_is_valid_primary_link(self):
        self.assert_linkability('Q104214134')

    def test_event_entry_that_is_actually_strongly_about_location(self):
        self.assert_linkability('Q5371519')

    def test_monastery_as_valid_primary_link(self):
        self.assert_linkability('Q4508631')
        self.assert_passing_all_tests({'wikidata': 'Q4508631', 'wikipedia': 'pl:Cziłter-Koba'})  # https://pl.wikipedia.org/wiki/Czi%C5%82ter-Koba

    def test_bridge_with_phantom_disambig_as_valid_primary_link(self):
        self.assert_passing_all_tests({'wikidata': 'Q55648855', 'wikipedia': 'he:גשר יהודית'})

    def test_detecting_weapon_model_as_invalid_primary_link(self):
        # https://www.openstreetmap.org/node/3014280721
        self.assert_unlinkability('Q266837')

        # https://www.openstreetmap.org/node/1331944863
        self.assert_unlinkability('Q7277047')

    def test_detecting_mine_disaster_as_invalid_primary_link(self):
        self.assert_unlinkability('Q4558986')

    def test_open_pit_mine_as_valid_primary_link(self):
        self.assert_linkability('Q2387872')
        self.assert_linkability('Q1323960')
        self.assert_linkability('Q2450901')

    def test_mine_shaft_as_valid_primary_link(self):
        self.assert_linkability('Q27132839')

    def test_underground_mine_as_valid_primary_link(self):
        self.assert_linkability('Q1408907')

    def test_movie_filming_location_as_valid_primary_link(self):
        self.assert_linkability('Q821784')

    def test_house_used_as_movie_filming_location_as_valid_primary_link(self):
        self.assert_linkability('Q60059405')

    def test_stairs_used_as_movie_filming_location_as_valid_primary_link(self):
        self.assert_linkability('Q74077989')

    def test_detecting_bombing_as_invalid_primary_link(self):
        self.assert_unlinkability('Q885225')

    def test_australian_administrative_boundary_as_valid_primary_link(self):
        # https://www.openstreetmap.org/relation/7032873
        self.assert_linkability('Q3179144')
        report = self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q3179144', "wikipedia")
        if report != None:
            self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q3179144', "wikipedia", show_debug=True)
        self.assert_passing_all_tests({'wikidata': 'Q3179144', 'wikipedia': 'en:Unincorporated Far West Region'})

    def test_pilgrimage_route_as_valid_primary_link(self):
        self.assert_linkability('Q41150')

    def test_fountain_as_valid_primary_link(self):
        self.assert_linkability('Q822122')

    def test_modern_artwork_as_valid_primary_link(self):
        self.assert_linkability('Q64435838')

    def test_river_source_as_valid_primary_link(self):
        self.assert_linkability('Q47037286')

    def test_old_house_as_valid_primary_link(self):
        self.assert_linkability('Q31147655')

    def test_ferry_route_as_valid_primary_link(self):
        self.assert_linkability('Q926453')

    def test_another_ferry_route_as_valid_primary_link(self):
        self.assert_linkability('Q2593299')

    def test_tram_system_as_valid_primary_link(self):
        # it is not a behavior...
        self.assert_linkability('Q9360797')

    def test_drug_treatment_center_as_valid_primary_link(self):
        self.assert_linkability('Q11143416')

    def test_pastoral_lease_as_valid_primary_link(self):
        self.assert_linkability('Q8293195')

    def test_park_and_node_beach_as_valid_primary_link(self):
        self.assert_linkability('Q5619268')

    def test_parish_as_valid_primary_link(self):
        # organisations are linkable
        self.assert_linkability('Q11808430')

    def test_local_bank_as_valid_primary_link(self):
        self.assert_linkability('Q9165022')

    def test_locality_as_valid_primary_link(self):
        self.assert_linkability('Q6412131')

    def test_murder_as_invalid_primary_link(self):
        self.assert_unlinkability('Q4468588')

    def test_circus_as_valid_primary_link(self):
        self.assert_linkability('Q4453469')

    def test_bar_as_valid_primary_link(self):
        self.assert_linkability('Q16910525')

    def test_industrial_spring_as_valid_primary_link(self):
        self.assert_linkability('Q2209005')

    def test_barracks_as_valid_primary_link(self):
        self.assert_linkability('Q16218254')

    def test_wikimedia_template_as_valid_primary_link(self):
        self.assert_unlinkability('Q25842885')

    def test_island_with_territorial_dispute_as_valid_primary_link(self):
        self.assert_linkability('Q598889')

    def test_district_with_specific_history_as_valid_primary_link(self):
        self.assert_linkability('Q64124')

    def test_unfinished_skyscraper_as_valid_primary_link(self):
        self.assert_linkability('Q25379780')

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

    def test_specific_christmas_shop_as_valid_primary_link(self):
        self.assert_linkability('Q1752539')

    def test_specific_observation_tower_as_valid_primary_link(self):
        self.assert_linkability('Q116445748')
        self.assert_linkability('Q113115337')

    def test_landslide_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q1946797')

    def test_landslide_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q27849294')

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

    def test_village_as_valid_primary_link(self):
        self.assert_linkability('Q43583')

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

    def test_batholith_as_valid_primary_link(self):
        self.assert_linkability('Q306201')
        self.assert_linkability('Q16901550')

    def test_chimney_as_valid_primary_link(self):
        self.assert_linkability('Q17792230')

    def test_exhibition_as_valid_primary_link(self):
        self.assert_linkability('Q63208613')

    def test_exhibition_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q2397171')

    def test_exhibition_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q105817457')

    def test_building_complex_as_valid_primary_link(self):
        self.assert_linkability('Q2319878')

    def test_palace_as_valid_primary_link(self):
        self.assert_linkability('Q11939856')
        self.assert_linkability('Q170495')

    def test_building_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q4583211')
        self.assert_linkability('Q22675345')

    def test_church_building_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q9333671')

    def test_church_building_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q9167695')

    def test_church_building_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q9167731')

    def test_church_building_as_valid_primary_link_testcase_d(self):
        self.assert_linkability('Q29890907')

    def test_aisleless_church_building_as_valid_primary_link(self):
        self.assert_linkability('Q1714172')
        self.assert_linkability('Q1742629')
        self.assert_linkability('Q1244438')
        self.assert_linkability('Q20754433')

    def test_swiss_church_building_as_valid_primary_link(self):
        # some botched mass edit in wikidata tagged buildings as religions
        self.assert_linkability('Q29211231')
        self.assert_linkability('Q3586114')
        self.assert_linkability('Q29891487')
        self.assert_linkability('Q29890700')
        self.assert_linkability('Q29890681')
        self.assert_linkability('Q29890885')
        self.assert_linkability('Q29890928')
        self.assert_linkability('Q29890731')
        self.assert_linkability('Q29890788')
        self.assert_linkability('Q29890752')
        self.assert_linkability('Q3585906')
        self.assert_linkability('Q29891095')
        self.assert_linkability('Q29890915')
        self.assert_linkability('Q29891087')
        self.assert_linkability('Q29891008')
        self.assert_linkability('Q1323184')
        self.assert_linkability('Q29890738')
        self.assert_linkability('Q2334476')
        self.assert_linkability('Q16266364')
        self.assert_linkability('Q1742845')
        self.assert_linkability('Q2137110')

    def test_land_art_as_valid_primary_link(self):
        self.assert_linkability('Q55723212')
        self.assert_linkability('Q99484886')

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

    def test_city_with_award_as_valid_primary_link(self):
        self.assert_linkability('Q1720')
        self.assert_linkability('Q2280')

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
        self.assert_linkability('Q11442821')
        self.assert_linkability('Q12279121')

    def test_specific_institution_as_valid_primary_link(self):
        self.assert_linkability('Q11713051')

    def test_coastal_defense_fort_as_valid_primary_link(self):
        self.assert_linkability('Q5472138')

    def test_coastal_defense_fort_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q22084285')

    def test_coastal_defense_fort_as_valid_primary_link_testcase_c(self):
        self.assert_linkability('Q5472172')
        # maybe "instance of coastal defence and fortification (Q5138347)" should just be silenced?

    def test_railing_as_valid_primary_link(self):
        self.assert_linkability('Q37818361')

    def test_monastery_with_peat_bath_as_valid_primary_link(self):
        self.assert_linkability('Q27914521')

    def test_monastery_town_as_valid_primary_link(self):
        self.assert_linkability('Q1265519')

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

    def test_power_plant_under_construction_as_valid_primary_link(self):
        self.assert_linkability('Q1630042')

    def test_railway_under_construction_as_valid_primary_link(self):
        self.assert_linkability('Q7985674')

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

    def test_radio_measuring_point_as_valid_primary_link(self):
        self.assert_linkability('Q19280069')

    def test_office_building_as_valid_primary_link(self):
        self.assert_linkability('Q1590873')
        self.assert_linkability('Q123510810')

    def test_station_of_a_cross_as_valid_primary_link(self):
        self.assert_linkability('Q98488381')

    def test_garden_as_valid_primary_link(self):
        self.assert_linkability('Q19575149')

    def test_that_defunct_monastery_is_not_an_event(self):
        self.is_not_an_event('Q28976876')

    def test_that_publisher_is_not_an_event(self):
        self.is_not_an_event('Q1668285')

    def test_that_organization_is_not_an_event(self):
        self.is_not_an_event('Q2457448')

    def test_that_bmw_ad_buildings_is_valid_primary_link(self):
        self.assert_linkability('Q699614')

    def test_that_university_organisation_is_not_an_event(self):
        self.is_not_an_event('Q106592334')

    def test_that_defunct_school_is_not_an_event(self):
        self.is_not_an_event('Q113019862')

    def test_that_hardened_shelter_is_not_aspect_of_geographic_region(self):
        self.is_not_a_specific_error_class('Q91939', 'an aspect in a geographic region')

    def test_that_training_ship_is_not_a_mental_process(self):
        self.is_not_a_specific_error_class('Q315820', 'a mental process')

    def test_that_propaganda_institution_is_not_a_mental_process(self):
        self.is_not_a_specific_error_class('Q157033', 'a mental process')

    def test_that_radar_network_is_not_a_mental_process(self):
        self.is_not_a_specific_error_class('Q378431', 'a mental process')

    def test_that_business_is_not_a_social_issue(self):
        self.is_not_a_specific_error_class('Q110699468', 'a social issue')

    def test_that_business_involved_in_software_is_not_a_software_but_is_unlinkable_anyway(self):
        self.is_not_a_specific_error_class('Q18349346', 'a software')
        # self.assert_unlinkability('Q18349346') TODO

    def test_that_data_protection_institution_is_not_a_profession(self):
        self.is_not_a_specific_error_class('Q55499784', 'a profession')

    def test_that_specific_position_is_not_a_profession_testcase_a(self):
        self.is_not_a_specific_error_class('Q7583851', 'a profession')

    def test_that_specific_position_is_not_a_profession_testcase_b(self):
        self.is_not_a_specific_error_class('Q449319', 'a profession')

    def test_that_specific_position_is_not_a_profession_testcase_c(self):
        self.is_not_a_specific_error_class('Q3368517', 'a profession')

    def test_that_specific_position_is_not_a_profession_testcase_d(self):
        self.is_not_a_specific_error_class('Q3882136', 'a profession')

    def test_that_russian_war_company_is_not_a_profession_but_is_unlinkable_anyway(self):
        self.is_not_a_specific_error_class('Q188508', 'a profession')
        #self.assert_unlinkability('Q188508') TODO

    def test_that_flight_school_is_not_a_human_activity(self):
        self.is_not_a_specific_error_class('Q4654871', 'a human activity')

    def test_that_flight_rescue_is_not_a_human_activity_testcase_a(self):
        self.is_not_a_specific_error_class('Q4043199', 'a human activity')

    def test_that_flight_rescue_is_not_a_human_activity_testcase_b(self):
        self.is_not_a_specific_error_class('Q1706756', 'a human activity')

    def test_that_company_is_not_an_economic_sector_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q1655072') TODO
        self.is_not_a_specific_error_class('Q1655072', 'an economic sector')

    # broken output, not sure why TODO
    #def test_that_literature_in_north_frisian_is_not_an_economic_sector_but_is_unlinkable_anyway(self):
    #    self.is_not_a_specific_error_class('Q28548', 'an economic sector')
    #    self.assert_unlinkability('Q28548')

    # broken output, not sure why TODO
    #def test_that_martial_art_is_not_an_economic_sector_but_is_unlinkable_anyway(self):
    #    self.is_not_a_specific_error_class('Q2279163', 'an economic sector')
    #    self.assert_unlinkability('Q2279163')

    def test_that_company_is_not_an_economic_sector_but_is_unlinkable_anyway_testcase_b(self):
        #self.assert_unlinkability('Q552581') TODO
        self.is_not_a_specific_error_class('Q552581', 'an economic sector')

    def test_that_company_is_not_an_economic_sector_but_is_unlinkable_anyway_testcase_c(self):
        #self.assert_unlinkability('Q173941') TODO
        self.is_not_a_specific_error_class('Q173941', 'an economic sector')

    def test_that_brand_is_not_a_food_but_is_unlinkable_anyway_testcase_b(self):
        self.assert_unlinkability('Q5129551')
        self.is_not_a_specific_error_class('Q5129551', 'a food')

    def test_that_distillery_is_not_a_food(self):
        self.is_not_a_specific_error_class('Q7225874', 'a food')
        self.assert_linkability('Q7225874')

    def test_that_insurance_company_is_not_insurance_but_is_unlinkable_anyway_testcase_a(self):
        #self.assert_unlinkability('Q5708804') # TODO
        self.is_not_a_specific_error_class('Q5708804', 'an insurance')

    def test_that_insurance_company_is_not_insurance_but_is_unlinkable_anyway_testcase_b(self):
        #self.assert_unlinkability('Q5723049') # TODO
        self.is_not_a_specific_error_class('Q5723049', 'an insurance')

    def test_that_insurance_company_is_not_insurance_but_is_unlinkable_anyway_testcase_c(self):
        #self.assert_unlinkability('Q657359') # TODO
        self.is_not_a_specific_error_class('Q657359', 'an insurance')
        

    def test_that_social_insurance_institution_is_not_insurance_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q1458480') # TODO
        self.is_not_a_specific_error_class('Q1458480', 'an insurance')


    def test_that_forest_kindegarten_is_valid_primary_link(self):
        self.assert_linkability('Q106974829')

    def test_that_community_fridge_is_not_a_general_industry_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q42417254') TODO - add test that will expect that it failed due to subclass instance
        self.is_not_a_specific_error_class('Q42417254', 'a general industry')

    def test_that_company_is_not_a_general_industry_testcase_a(self):
        self.is_not_a_specific_error_class('Q2539159', 'a general industry')

    def test_that_company_is_not_a_general_industry_testcase_b(self):
        self.is_not_a_specific_error_class('Q114324216', 'a general industry')
        
    def test_that_organisation_is_not_a_general_industry_testcase_a(self):
        self.is_not_a_specific_error_class('Q1201729', 'a general industry')

    def test_that_bombing_is_not_a_general_industry_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q1875563')
        #self.is_not_a_specific_error_class('Q1875563', 'a general industry') TODO reenable once I run out of other problems and it is fixed

    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_a(self):
        #self.assert_unlinkability('Q1703172') TODO
        self.is_not_a_specific_error_class('Q1703172', 'a general industry')

    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_b(self):
        #self.assert_unlinkability('Q3027764') TODO
        self.is_not_a_specific_error_class('Q3027764', 'a general industry')

        #self.assert_unlinkability('Q166561') TODO
        self.is_not_a_specific_error_class('Q166561', 'a general industry')
        
    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_c(self):
        #self.assert_unlinkability('Q96018061') TODO
        self.is_not_a_specific_error_class('Q96018061', 'a general industry')

    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_d(self):
        #self.assert_unlinkability('Q63327') TODO
        self.is_not_a_specific_error_class('Q63327', 'a general industry')

    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_e(self):
        #self.assert_unlinkability('Q495943') TODO
        self.is_not_a_specific_error_class('Q495943', 'a general industry')

    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_f(self):
        #self.assert_unlinkability('Q85866624') TODO
        self.is_not_a_specific_error_class('Q85866624', 'a general industry')

    def test_that_company_is_not_a_general_industry_but_is_unlinkable_anyway_testcase_g(self):
        #self.assert_unlinkability('Q22868') TODO
        self.is_not_a_specific_error_class('Q22868', 'a general industry')

    def test_that_online_shop_company_is_not_a_general_industry_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q23827008')
        #self.is_not_a_specific_error_class('Q23827008', 'a general industry') TODO - enable after all wikidata issues are cleaned

        self.assert_unlinkability('Q95578521')
        #self.is_not_a_specific_error_class('Q95578521', 'a general industry') TODO - enable after all wikidata issues are cleaned

    def test_that_mountain_rescue_organization_is_not_an_economic_sector_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q306066')
        self.is_not_a_specific_error_class('Q4654871', 'an economic sector')

    def test_that_mural_is_not_a_academic_discipline(self):
        self.is_not_a_specific_error_class('Q219423', 'an academic discipline')

    def test_that_organisation_is_not_a_academic_discipline(self):
        self.is_not_a_specific_error_class('Q7817', 'an academic discipline')

    def test_that_gay_parade_is_not_a_academic_discipline_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q7242733')
        self.is_not_a_specific_error_class('Q7242733', 'an academic discipline')

    def test_that_language_is_not_a_academic_discipline_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q32641')
        self.is_not_a_specific_error_class('Q32641', 'an academic discipline')

    def test_that_type_of_pastoralism_is_not_a_academic_discipline_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q4657754') TODO - why it is triggered?
        self.is_not_a_specific_error_class('Q4657754', 'an academic discipline')

    def test_that_organisation_is_not_an_award(self):
        self.is_not_a_specific_error_class('Q856355', 'an award')
        self.is_not_a_specific_error_class('Q5324438', 'an award')

    def test_that_minister_or_other_administartor_is_not_an_award(self):
        self.is_not_a_specific_error_class('Q107919654', 'an award')
        self.is_not_a_specific_error_class('Q11739165', 'an award')

    def test_that_cofee_variety_is_not_a_academic_discipline_but_is_invalid_to_link_anyway(self):
        self.assert_unlinkability('Q97160325')
        self.is_not_a_specific_error_class('Q97160325', 'an academic discipline')

    def test_that_drug_rehabilitation_community_is_not_an_event(self):
        self.is_not_an_event('Q2219871')

    def test_that_diet_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q3132857')
        self.is_not_an_event('Q3132857')

    def test_that_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q37156')  # IBM
        self.is_not_an_event('Q37156')
        self.is_not_a_behavior('Q37156')

    def test_that_railway_operator_is_not_behavior_but_is_unlinkable_anyway(self):
        #self.assert_unlinkability('Q1814208') TODO - enable once mass exceptions in workarounds_for_wikidata_bugs_breakage_and_mistakes are gone
        self.is_not_an_event('Q1814208')
        self.is_not_a_behavior('Q1814208')

    def test_that_postal_delivery_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q1093368')
        self.is_not_an_event('Q1093368')
        self.is_not_a_behavior('Q1093368')

    def test_that_company_making_events_is_not_an_event(self):
        self.is_not_an_event('Q3093234')
        self.is_not_a_behavior('Q3093234')
        # TODO - it is not a valid link either

    def test_that_software_company_is_not_an_event_but_is_unlinkable_anyway(self):
        self.assert_unlinkability('Q468381')  # Avira
        self.is_not_an_event('Q468381')
        self.is_not_a_behavior('Q468381')

    def test_that_software_company_is_not_an_event_but_is_unlinkable_anyway_testcase_b(self):
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

    def test_that_traffic_sign_parody_is_linkable(self):
        self.assert_linkability('Q119895157')

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

    def test_that_gondola_lift_is_valid_link(self):
        self.assert_linkability('Q16589533')

    def test_that_specific_waterfront_development_is_valid_link(self):
        self.assert_linkability('Q5363395')

    def test_that_wine_region_is_valid_link(self):
        self.assert_linkability('Q24521756')  # though winde region itself seems unmappable in OSM...

    def test_that_charity_organization_is_not_an_event_or_behavior(self):
        self.is_not_an_event('Q7075332')
        self.is_not_a_behavior('Q7075332')

    def test_that_married_couple_an_event_or_behavior(self):
        self.is_not_an_event('Q3051246')
        self.is_not_a_behavior('Q3051246')

    def test_that_organisation_is_not_an_event(self):
        self.is_not_an_event('Q15852617')

    def test_that_organisation_is_not_an_event_testcase_b(self):
        self.is_not_an_event('Q596850')

    def test_that_organisation_is_not_an_event_testcase_c(self):
        self.is_not_an_event('Q20105386')

    def test_that_university_is_not_an_event(self):
        self.is_not_an_event('Q6156487')

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

    def test_catalitic_tower_as_valid_primary_link(self):
        self.assert_linkability('Q122211991')

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
        pass
        #self.assert_unlinkability('Q2363543') TODO (at least wait for Wikidata community to fix known fixable issues)

    def test_grafitti_wall_as_valid_primary_link(self):
        self.assert_linkability('Q69689708')

    def test_general_grafitti_article_as_unvalid_primary_link(self):
        self.assert_unlinkability('Q23097882')

    def test_prehistoric_settlement_as_valid_primary_link(self):
        self.assert_linkability('Q1015819')

    def test_historic_site_as_valid_primary_link(self):
        self.assert_linkability('Q104868895')

    def test_historic_site_apparently_technical_one_as_valid_primary_link(self):
        self.assert_linkability('Q98581751')

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

    def test_apparatus_as_valid_primary_link(self):
        self.assert_linkability('Q316053')

    def test_post_office_building_as_valid_primary_link(self):
        self.assert_linkability('Q49593062')

    def test_squatted_building_as_valid_primary_link(self):
        self.assert_linkability('Q15303877')

    def test_town_as_valid_primary_link(self):
        self.assert_linkability('Q16106')

    def test_folklore_related_town_as_valid_primary_link(self):
        self.assert_linkability('Q569625')

    def test_seaport_town_as_valid_primary_link(self):
        self.assert_linkability('Q935686')

    def test_seaport_as_valid_primary_link(self):
        self.assert_linkability('Q883613')

    def test_petroglyph_as_valid_primary_link(self):
        self.assert_linkability('Q552106')
        self.assert_linkability('Q1637649')
        self.assert_linkability('Q16334471')

    def test_research_center_as_valid_primary_link(self):
        self.assert_linkability('Q12062400')

    def test_children_center_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q706474', 'an intentional human activity')

    def test_company_is_not_industry_by_itself(self):
        self.is_not_a_specific_error_class('Q18914701', 'an intentional human activity')

    def test_puppet_theater_is_not_puppetry(self):
        self.is_not_a_specific_error_class('Q293894', 'an intentional human activity')

    def test_shop_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q24693696', 'an intentional human activity')

    def test_settlement_is_linkable(self):
        self.is_not_a_specific_error_class('Q1012502', 'an award')
        self.assert_linkability('Q1012502')
        self.assert_linkability('Q160642')
        self.assert_linkability('Q204720')
        self.assert_linkability('Q207736')
        self.assert_linkability('Q160642')

    def test_drinking_water_fountain_style_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q1062192', 'an intentional human activity')
        #self.assert_unlinkability('Q1062192') TODO - for later, once Wikidata is fixed

    def test_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q215392', 'an intentional human activity')
        # TODO - it is not a valid link either

    def test_another_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q1814208', 'an intentional human activity')
        # TODO - it is not a valid link either

    def test_municipal_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q1285495', 'an intentional human activity')
        # TODO - it is not a valid link either

    def test_fair_trade_company_is_not_an_intentional_human_activity(self):
        self.is_not_a_specific_error_class('Q896100', 'an intentional human activity')
        # TODO - it is not a valid link either

    def test_ridesharing_company_is_not_a_legal_action(self):
        self.is_not_a_specific_error_class('Q692400', 'an intentional human activity')
        self.is_not_a_specific_error_class('Q692400', 'a legal action')
        # TODO - it is not a valid link either

    def test_endowed_organization_is_not_a_legal_action(self):
        self.is_not_a_specific_error_class('Q1205496', 'a legal action')

    def testcity_garm_is_not_a_legal_action(self):
        self.is_not_a_specific_error_class('Q75172691', 'a legal action')

    def test_letter_is_not_tradition(self):
        self.is_not_a_specific_error_class('Q9963', 'a tradition')

    def test_hosting_company_is_not_a_legal_action(self):
        self.is_not_a_specific_error_class('Q6554704', 'an intentional human activity')
        self.is_not_a_specific_error_class('Q6554704', 'a legal action')
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

    def test_railway_troops_are_not_a_research(self):
        self.is_not_a_specific_error_class('Q1256346', 'a research')

    def test_abandoned_village_is_not_a_research(self):
        self.is_not_a_specific_error_class('Q1977339', 'a research')

    def test_roman_fort_is_not_a_research(self):
        self.is_not_a_specific_error_class('Q1243550', 'a research')

    def test_apostle_is_not_fictional_but_still_invalid(self):
        self.is_not_a_specific_error_class('Q51672', 'a fictional entity')
        tags = {"wikidata": "Q51672"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        if "fictional" in problem.data()['error_id']:
            print(problem.data()['error_id'])
            self.assertNotEqual(True, "fictional" in problem.data()['error_id'])

    def test_herod_is_not_fictional_but_still_invalid_link(self):
        self.is_not_a_specific_error_class('Q43945', 'a fictional entity')
        tags = {"wikidata": "Q43945"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        self.assertNotEqual(None, problem)
        if "fictional" in problem.data()['error_id']:
            print(problem.data()['error_id'])
            self.assertNotEqual(True, "fictional" in problem.data()['error_id'])

    def test_jesus_is_not_fictional_but_still_invalid_link(self):
        # https://en.wikipedia.org/wiki/Historicity_of_Jesus
        self.is_not_a_specific_error_class('Q302', 'a fictional entity')
        tags = {"wikidata": "Q302"}
        location = None
        object_description = "fake test object"
        problem = self.detector().freely_reorderable_issue_reports(object_description, location, tags)
        return  # TODO: requires fixing various wikidata issues, see https://www.wikidata.org/w/index.php?title=User:Mateusz_Konieczny/failing_testcases&oldid=1940322493#Jesus_(Q302)_is_a_fictional_entity,_according_to_Wikidata_ontology
        self.assertNotEqual(None, problem)
        if "fictional" in problem.data()['error_id']:
            print(problem.data()['error_id'])
            self.assertNotEqual(True, "fictional" in problem.data()['error_id'])

    def test_street_with_brothels_as_valid_primary_link(self):
        self.assert_linkability('Q1877599')

    def test_promenade_as_valid_primary_link(self):
        self.assert_linkability('Q15052053')

    def test_brothel_as_valid_primary_link(self):
        self.assert_linkability('Q4745250')

    def test_abandoned_company_town_as_valid_primary_link(self):
        self.assert_linkability('Q113997708')

    def test_company_town_as_valid_primary_link(self):
        self.assert_linkability('Q656628')

    def test_cave_nature_reserve_as_valid_primary_link(self):
        self.assert_linkability('Q116396391')

    def test_rancho_as_valid_primary_link(self):
        self.assert_linkability('Q7290956')

    def test_island_rancho_as_valid_primary_link(self):
        self.assert_linkability('Q845229')

    def test_ugly_sculpture_as_valid_primary_link(self):
        self.assert_linkability('Q445256')
        self.assert_linkability('Q108343850')

    def test_telescope_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q1632481')

    def test_telescope_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q1513315')

    def test_distributed_telescope_as_valid_primary_link(self):
        self.assert_linkability('Q1192324')

    def test_canal_as_valid_primary_link(self):
        self.assert_linkability('Q63684450')

    def test_sound_stage_as_valid_primary_link(self):
        self.assert_linkability('Q60686172')

    def test_canopy_walkway_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q27478902')

    def test_canopy_walkway_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q64760026')

    def test_industrial_region_as_valid_primary_link(self):
        self.assert_linkability('Q7303912')

    def test_andorra_country_as_valid_primary_link(self):
        self.assert_linkability('Q228')

    def test_educational_company_is_not_an_event(self):
        self.is_not_an_event('Q661869')
        # TODO - it is not a valid link either

    def test_ore_is_not_event_and_is_not_linkable(self):
        self.is_not_an_event('Q102798')
        self.assert_failing_full_tests('Q102798', 'en:Ore')

    def test_mineral_is_not_event_and_is_not_linkable(self):
        self.is_not_an_event('Q7946')
        self.assert_failing_full_tests('Q7946', 'en:Mineral')

    def test_government_institution_is_not_event(self):
        self.is_not_an_event('Q8349981')

    def test_detect_battle_more_specifically_than_generic_event_testcase_a(self):
        self.is_not_an_event('Q4087439')

    def test_detect_battle_more_specifically_than_generic_event_testcase_b(self):
        self.is_not_an_event('Q677959')

    def test_school_as_valid_primary_link(self):
        # if something affects all schools, single report is preferable
        self.assert_linkability('Q4059246')
        self.assert_linkability('Q5038462')
        self.assert_linkability('Q7743365')

    def test_state_school_as_valid_primary_link(self):
        self.assert_linkability('Q1201799')
        self.assert_linkability('Q108900690')

    def test_special_education_school_as_valid_primary_link(self):
        self.assert_linkability('Q97737556')

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

    def test_ruined_castle_as_valid_primary_link(self):
        self.assert_linkability('Q1663659')

    def test_ruined_rock_as_valid_primary_link(self):
        self.assert_linkability('Q7101413')

    def test_gravity_hill_optical_illusion_as_valid_primary_link(self):
        self.assert_linkability('Q9156011')

    def test_library_as_valid_primary_link(self):
        self.assert_linkability('Q11551945')

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

    def test_amusement_monorail_as_valid_primary_link(self):
        self.assert_linkability('Q2126693')

    def test_summer_camp_as_valid_primary_link(self):
        self.assert_linkability('Q5027247')

    def test_university_campus_as_valid_primary_link(self):
        self.assert_linkability('Q4066906')

    def test_building_part_as_valid_primary_link(self):
        self.assert_linkability('Q76012362')

    def test_maybe_defunct_car_cemetery_as_valid_primary_link(self):
        self.assert_linkability('Q1620927')

    def test_that_studies_center_is_not_an_event(self):
        self.is_not_an_event('Q106592334')

    def test_that_motif_is_not_an_event(self):
        self.is_not_an_event('Q447201')

    def test_that_association_is_not_an_event(self):
        self.is_not_an_event('Q157033')

    def test_islamic_army_is_not_an_event(self):
        self.is_not_an_event('Q271110')

    def test_tree_or_more_specifically_clonal_colony_as_valid_primary_link(self):
        self.assert_linkability('Q19865287')

    def test_geotope_as_valid_primary_link(self):
        self.assert_linkability('Q48261221')

    def test_archeological_site_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q66815081')

    def test_arty_pedestrian_bridge_as_valid_primary_link(self):
        self.assert_linkability('Q65594284')

    def test_sculpture_garden_as_valid_primary_link(self):
        self.assert_linkability('Q860863')

    def test_gorge_as_valid_primary_link(self):
        self.assert_linkability('Q1647633')

    def test_former_city_as_valid_primary_link(self):
        self.assert_linkability('Q608095')

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

    def test_holocaust_is_not_a_physical_process_but_is_not_linkable_anyway(self):
        self.is_not_a_specific_error_class('Q2763', 'a physical process')
        self.assert_unlinkability('Q2763')

    def test_aircraft_model_is_not_a_physical_process_but_is_not_linkable_anyway(self):
        self.is_not_a_specific_error_class('Q1390439', 'a physical process')
        #self.assert_unlinkability('Q1390439') TODO enable after wikidata is fixed

    def test_railway_line_is_not_a_physical_process(self):
        self.is_not_a_specific_error_class('Q7578675', 'a physical process')

    def test_refinery_as_valid_primary_link(self):
        self.assert_linkability('Q3417387')

    def test_archeological_remnants_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q108990211')

    def test_archeological_remnants_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q108987278')

    def test_military_base_as_valid_primary_link(self):
        self.assert_linkability('Q62092177')

    def test_recreation_area_as_valid_primary_link(self):
        self.assert_linkability('Q7324253')

    def test_theater_as_valid_primary_link(self):
        self.assert_linkability('Q16879523')

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

    def test_specific_cinema_as_valid_primary_link(self):
        self.assert_linkability('Q34379615')

    def test_fictional_island_as_invalid_primary_link(self):
        self.assert_unlinkability('Q1877267')

    def test_features_of_firefox_as_invalid_primary_link(self):
        self.assert_unlinkability('Q459708')

    def test_taxon_as_invalid_primary_link(self):
        self.assert_unlinkability('Q159570')
        self.assert_unlinkability('Q26899')
        self.assert_unlinkability('Q26771')
        self.assert_unlinkability('Q158746')

    def test_artist_colony_as_valid_primary_link(self):
        self.assert_linkability('Q2598870')

    def test_nonexistence_of_defunct_brand(self):
        # https://www.openstreetmap.org/note/3820933 see for potential valid test case
        self.assertNotEqual(None, self.detector().check_is_object_brand_is_existing({"brand:wikidata": "Q7501155"}))

    def test_existence_of_resurrected_brand(self):
        self.brand_still_exists("Q1891407", "??", "TODO: missing reference")

    def test_former_company_exists_as_a_brand_texaco(self):
        # Texaco
        self.brand_still_exists("Q1891407", "Texaco", "TODO: missing reference for Texaco")

    def test_former_company_exists_as_a_brand_radioshack(self):
        self.brand_still_exists("Q1195490", "RadioShack", 'https://en.wikipedia.org/w/index.php?title=RadioShack&oldid=1169051112 mentions "network of independently owned and franchised RadioShack stores"')

    def test_former_company_exists_as_a_brand_amoco(self):
        self.brand_still_exists("Q465952", "Amoco", 'https://en.wikipedia.org/w/index.php?title=Amoco&oldid=1169009405 : Merged with BP, becoming a brand')

    def test_former_company_exists_as_a_brand_lotos(self):
        self.brand_still_exists("Q1256909", "Lotos", 'company sold, Orlen bought fuel stations rebranded, brand active at at least some MOL-owned ones (as of 2023-08)')

    def test_agip_apparently_exists(self):
        self.brand_still_exists("Q377915", "Agip", 'branding reported to be in use - see https://www.openstreetmap.org/note/3821330')

    def test_former_company_exists_as_a_brand_conoco(self):
        self.brand_still_exists("Q1126518", "Conoco", 'https://en.wikipedia.org/w/index.php?title=Conoco&oldid=1156282755 "Currently the name Conoco is a brand of gasoline and service station in the United States"')

    def test_former_company_exists_as_a_brand_gulf(self):
        self.brand_still_exists("Q1296860", "Gulf Oil", 'https://en.wikipedia.org/wiki/en:Gulf Oil "In Spain and Portugal, the Gulf brand is now owned by TotalEnergies SE.[5]"')

    def test_unexplained_closure_claim(self):
        self.brand_still_exists("Q3888718", "Paddy Power", 'https://en.wikipedia.org/wiki/en:Paddy_Power seems to describe it as existing and operational')

    def test_such_surveillance_is_not_illegal_in_all_cases(self):
        self.is_not_a_specific_error_class('Q387115', 'a violation of law')

    def test_decide_is_it_about_site_or_pseuodarchelogy_case(self):
        self.is_not_a_specific_error_class('Q1267546', 'a social issue')

    def test_plantation_as_valid_primary_link(self):
        self.assert_linkability('Q23734811')
