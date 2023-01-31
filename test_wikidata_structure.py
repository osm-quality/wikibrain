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

    def is_unlinkable_check(self, type_id):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        return self.detector().get_error_report_if_type_unlinkable_as_primary(type_id, {})
        # get_error_report_if_type_unlinkable_as_primary
        #return self.detector().get_error_report_if_secondary_wikipedia_tag_should_be_used(type_id, {})
    
    def is_not_an_event(self, type_id):
        self.is_not_a_specific_error_class(type_id, 'an event')

    def is_not_a_behavior(self, type_id):
        self.is_not_a_specific_error_class(type_id, 'a behavior')
        self.is_not_a_specific_error_class(type_id, 'a human behavior')

    def is_not_a_specific_error_class(self, type_id, error_class):
        potential_failure = self.detector().get_reason_why_type_makes_object_invalid_primary_link(type_id)
        if potential_failure == None:
            return
        if potential_failure['what'] == error_class:
            self.detector().output_debug_about_wikidata_item(wikidata_id)
            self.assertEqual(potential_failure['what'], expected_error)

    def dump_debug_into_stdout(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable != None:
            #print("is_unlinkable.error_message")
            #print(is_unlinkable.error_message)
            print()
            print()
            print("https://www.wikidata.org/wiki/" + type_id)
            print("https://www.wikidata.org/wiki/Wikidata_talk:WikiProject_Ontology")
            print()
            invalid_groups = self.detector().invalid_types()
            reported_already = [] # sometimes the same problem name has multiple invalid types pointing to it
            # in such case it should be still reported once
            for key in invalid_groups:
                possible_match = invalid_groups[key]["what"]
                if "is about " + possible_match + ", so it is very unlikely to be correct" in is_unlinkable.error_message:
                    if possible_match not in reported_already:
                        print("== {{Q|" + type_id + "}} is " + possible_match + ", according to Wikidata ontology ==")
                        reported_already.append(possible_match)
            print()
            #print("is_unlinkable.data")
            #print(is_unlinkable.data())
            #print(is_unlinkable.yaml_output())
        self.detector().dump_base_types_of_object_in_stdout(type_id, 'tests')
        print()

    def assert_linkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable != None:
            self.dump_debug_into_stdout(type_id)
        self.assertEqual(None, is_unlinkable)

    def assert_unlinkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable == None:
            self.dump_debug_into_stdout(type_id)
        self.assertNotEqual(None, is_unlinkable)

    def test_rejects_links_to_events(self):
        self.assert_unlinkability('Q134301')

    def test_rejects_links_to_events_case_of_hinderburg_disaster(self):
        self.assert_unlinkability('Q3182723')

    def test_rejects_links_to_events_case_of_a_battle(self):
        self.assert_unlinkability('Q663435')

    def test_rejects_links_to_spacecraft(self):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        self.assertNotEqual(None, self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q2513'))

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

    def test_detecting_castle_as_valid_primary_link(self):
        self.assert_linkability('Q2106892')

    def test_detecting_reconstructed_castle_as_valid_primary_link(self):
        self.assert_linkability('Q2461065')

    def test_detecting_reconstructed_gate_as_valid_primary_link(self):
        self.assert_linkability('Q30035365')

    def test_detecting_fort_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q20089971')

    def test_detecting_fort_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q865131')

    def test_detecting_roundabout_art_as_valid_primary_link(self):
        self.assert_linkability('Q105414527')

    def test_detecting_funicular_as_valid_primary_link(self):
        self.assert_linkability('Q5614426')

    def test_detecting_fast_tram_as_valid_primary_link(self):
        self.assert_linkability('Q1814872')

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
        
    def test_geoglyph_as_valid_primary_link(self):
        self.assert_linkability('Q7717476') # not an event - via Q12060132 ("hillside letter" that is not a signage, it is product of a signage)

    def test_dunes_as_valid_primary_link(self):
        self.assert_linkability('Q1130721') # not an event - aeolian landform (Q4687862) is not sublass of aeolian process, natural object is not sublass of natural phenonemon ( https://www.wikidata.org/w/index.php?title=Q29651224&action=history )

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

    def test_protected_landscape_area_as_valid_primary_link(self):
        self.assert_linkability('Q8465509')

    def test_headquarters_landscape_area_as_valid_primary_link(self):
        self.assert_linkability('Q5578587')

    def test_museum_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q731126')

    def test_museum_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q27490233')

    def test_museum_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q9337658')

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

    def test_sign_as_valid_primary_link(self):
        # see https://www.wikidata.org/w/index.php?title=Wikidata%3AProject_chat&type=revision&diff=1358269822&oldid=1358263283
        # https://www.wikidata.org/w/index.php?title=Wikidata:Project_chat&diff=prev&oldid=1359638515
        self.assert_linkability('Q4804421')

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

    def test_artwork_as_valid_primary_link(self):
        self.assert_linkability('Q57838673')

    def test_gate_as_valid_primary_link(self):
        self.assert_linkability('Q26317425')

    def test_cricket_club_as_valid_primary_link(self):
        self.assert_linkability('Q3195284')

    def test_meridian_as_valid_primary_link(self):
        self.assert_linkability('Q131108')

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

    def test_chapel_as_valid_primary_link(self):
        self.assert_linkability('Q4993989')

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

    def test_australian_administrative_boundary_as_valid_primary_link(self):
        # https://www.openstreetmap.org/relation/7032873
        self.assert_linkability('Q3179144')
        report = self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q3179144')
        if report != None:
            self.detector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q3179144', show_debug=True)
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

    def test_glassworks_as_valid_primary_link(self):
        self.assert_linkability('Q63124776')

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

    def test_church_building_as_valid_primary_link_testcase_a(self):
        self.assert_linkability('Q9333671')

    def test_church_building_as_valid_primary_link_testcase_b(self):
        self.assert_linkability('Q9167695')

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

    def test_coastal_defense_fort_as_valid_primary_link(self):
        self.assert_linkability('Q5472138')

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

    def test_power_cable_as_valid_primary_link(self):
        self.assert_linkability('Q314180')

    def test_power_station_as_valid_primary_link(self):
        self.assert_linkability('Q19378684')

    def test_ranch_as_valid_primary_link(self):
        self.assert_linkability('Q7185999')

    def test_mall_as_valid_primary_link(self):
        self.assert_linkability('Q9265538')

    def test_wall_as_valid_primary_link(self):
        self.assert_linkability('Q1543119')

    def test_office_building_as_valid_primary_link(self):
        self.assert_linkability('Q1590873')

    def test_that_software_is_not_an_event(self):
        self.is_not_an_event('Q25874683')

    def test_that_organisation_is_not_an_event(self):
        self.is_not_an_event('Q15852617')

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

    def test_theme_park_as_valid_primary_link(self):
        self.assert_linkability('Q14531179')

    def test_college_as_valid_primary_link(self):
        self.assert_linkability('Q884105')

    def test_specific_building_as_valid_primary_link(self):
        self.assert_linkability('Q15807394')

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

    def test_bicycle_sharing_system_is_not_human_behavior(self):
        self.is_not_a_behavior('Q3555363')

    def test_wikimedia_deutschland_is_not_human_behavior(self):
        self.is_not_a_behavior('Q8288')

    def test_ngo_is_not_human_behavior(self):
        self.is_not_a_behavior('Q2363543')

    def test_ngo_as_invalid_primary_link(self):
        self.is_not_a_behavior('Q2363543')

    def test_grafitti_wall_as_valid_primary_link(self):
        self.assert_linkability('Q69689708')

    def test_prehistoric_settlement_as_valid_primary_link(self):
        self.assert_linkability('Q1015819')
