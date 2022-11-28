import unittest
from wikibrain import wikimedia_link_issue_reporter
import wikimedia_connection.wikimedia_connection as wikimedia_connection
import osm_handling_config.global_config as osm_handling_config
import wikimedia_connection.wikidata_processing as wikidata_processing

class WikidataTests(unittest.TestCase):
    def assert_passing_all_tests(self, wikidata, wikipedia):
        tags = {'wikidata': wikidata, 'wikipedia': wikipedia}
        location = (0, 0)
        object_type = "node"
        object_description = "test"
        report = wikimedia_link_issue_reporter.WikimediaLinkIssueDetector().get_the_most_important_problem_generic(tags, location, object_type, object_description)
        if report != None:
            print(report.data())
        self.assertEqual(None, report)

    def is_unlinkable_check(self, type_id):
        wikimedia_connection.set_cache_location(osm_handling_config.get_wikimedia_connection_cache_location())
        return wikimedia_link_issue_reporter.WikimediaLinkIssueDetector().get_error_report_if_type_unlinkable_as_primary(type_id, {})

    def dump_debug_into_stdout(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        wikimedia_link_issue_reporter.WikimediaLinkIssueDetector().dump_base_types_of_object_in_stdout(type_id, 'tests')
        print()
        if is_unlinkable != None:
            print("is_unlinkable.error_message")
            print(is_unlinkable.error_message)
            if "is about an object that exists outside physical reality, so it is very unlikely to be correct" in is_unlinkable.error_message:
                print()
                print()
                print()
                print()
                print("============================== title")
                print("{{Q|" + type_id + "}} is object that exists outside physical reality, according to Wikidata ontology")
                print()
                print()
                print()
            print("is_unlinkable.data")
            print(is_unlinkable.data())
            #print(is_unlinkable.yaml_output())

    def assert_linkability(self, type_id):
        is_unlinkable = self.is_unlinkable_check(type_id)
        if is_unlinkable != None:
            self.dump_debug_into_stdout(type_id)
            print("-------------")
            print(is_unlinkable.data()['error_message'])
            print(("-------------"))
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
        self.assertNotEqual(None, wikimedia_link_issue_reporter.WikimediaLinkIssueDetector().get_error_report_if_property_indicates_that_it_is_unlinkable_as_primary('Q2513'))

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

    def test_detecting_funicular_as_valid_primary_link(self):
        self.assert_linkability('Q5614426')

    def test_detecting_fast_tram_as_valid_primary_link(self):
        self.assert_linkability('Q1814872')

    def test_detecting_high_school_as_valid_primary_link(self):
        self.assert_linkability('Q9296000')

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

    def test_tree_as_valid_primary_link(self):
        self.assert_linkability('Q6703503') # not an event

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

    def test_megaproject_as_valid_primary_link(self):
        self.assert_linkability('Q782093') # some megaprojects are already existing, project ( https://www.wikidata.org/wiki/Q170584 ) may be already complete

    def test_pilgrim_route_as_valid_primary_link(self):
        self.assert_linkability('Q829469')
 
    def test_botanical_garden_as_valid_primary_link(self):
        self.assert_linkability('Q589884')
       
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

    def test_cafe_as_valid_primary_link(self):
        self.assert_linkability('Q672804')

    def test_religious_administrative_area_as_valid_primary_link(self):
        self.assert_linkability('Q1364786')

    def test_administrative_area_as_valid_primary_link(self):
        self.assert_linkability('Q1144105')

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

    def test_museum_as_valid_primary_link(self):
        self.assert_linkability('Q731126')

    def test_mural_as_valid_primary_link(self):
        self.assert_linkability('Q29351056')
        self.assert_linkability('Q94279877')
        
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

    def test_collosal_statue_as_valid_primary_link(self):
        self.assert_linkability('Q805442')

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

    def test_sculpure_as_valid_primary_link(self):
        self.assert_linkability('Q105492941')

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

    def test_specific_locomotive_as_valid_primary_link(self):
        self.assert_linkability('Q113278632')
        self.assert_passing_all_tests('Q113278632', 'en:Santa Fe 769')


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

    def test_monastery_as_valid_primary_link(self):
        self.assert_linkability('Q4508631')
        self.assert_passing_all_tests('Q4508631', 'pl:Cziłter-Koba') # https://pl.wikipedia.org/wiki/Czi%C5%82ter-Koba

    def test_detecting_weapon_model_as_invalid_primary_link(self):
        # https://www.openstreetmap.org/node/3014280721
        self.assert_unlinkability('Q266837')

        # https://www.openstreetmap.org/node/1331944863
        self.assert_unlinkability('Q7277047')

    def test_pole_of_inaccessibility_as_valid_primary_link(self):
        # https://www.openstreetmap.org/node/3001893677
        self.assert_linkability('Q752003')
        self.assert_passing_all_tests('Q752003', 'en:Pole of inaccessibility')

    def test_australian_administartive_boundary_as_valid_primary_link(self):
        # https://www.openstreetmap.org/relation/7032873
        self.assert_linkability('Q3179144')
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
