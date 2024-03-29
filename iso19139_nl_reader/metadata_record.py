import os.path
from urllib.parse import parse_qs, urlparse
import pkg_resources
import lxml.etree as et
from .util import is_url

class WarningError(Exception):
    pass

class MetadataRecord():
    def __init__(self, md_file):
        xml_string = md_file.read().encode("utf-8")
        xpath_metadata = "/gmd:MD_Metadata"

        self.xml_string = xml_string
        self.etree = et.fromstring(xml_string)
        self.xpath_metadata = xpath_metadata
        self.xpath_record_type = f"{xpath_metadata}/gmd:hierarchyLevel/gmd:MD_ScopeCode"

        self.namespaces = {
            "csw": "http://www.opengis.net/cat/csw/2.0.2",
            "gco": "http://www.isotc211.org/2005/gco",
            "geonet": "http://www.fao.org/geonetwork",
            "gmd": "http://www.isotc211.org/2005/gmd",
            "gml": "http://www.opengis.net/gml",
            "gmx": "http://www.isotc211.org/2005/gmx",
            "gsr": "http://www.isotc211.org/2005/gsr",
            "gts": "http://www.isotc211.org/2005/gts",
            "srv": "http://www.isotc211.org/2005/srv",
            "xlink": "http://www.w3.org/1999/xlink",
        }
        self.service_types = {
            "OGC:CSW": "CSW",
            "OGC:WMS": "WMS",
            "OGC:WMTS": "WMTS",
            "OGC:WFS": "WFS",
            "OGC:WCS": "WCS",
            "OGC:SOS": "SOS",
            "INSPIRE Atom": "ATOM",
            "UKST": "TMS"
        }
        self.record_type = self.get_recordtype()
        if self.record_type == "service":
            self.xpath_resource_identification = f"{xpath_metadata}/gmd:identificationInfo/srv:SV_ServiceIdentification"
        elif self.record_type == "dataset":
            self.xpath_resource_identification = f"{xpath_metadata}/gmd:identificationInfo/gmd:MD_DataIdentification"
        self.metadata_id = self.get_mdidentifier()

    def get_single_xpath_value(self, xpath, etree=None):
        if etree is None:
            etree = self.etree
        result = etree.xpath(xpath, namespaces=self.namespaces)
        if result:
            return result[0].text
        return None

    def get_single_xpath_att(self, xpath, etree=None):
        if etree is None:
            etree = self.etree
        result = etree.xpath(xpath, namespaces=self.namespaces)
        if result:
            return result[0]
        return None

    def get_ogc_servicetype(self):
        xpath = f"{self.xpath_metadata}/gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource"
        xpath_prot = f"{xpath}/gmd:protocol/gco:CharacterString"
        protocol = self.get_single_xpath_value(xpath_prot)
        if protocol is None:
            xpath_prot = f"{xpath}/gmd:protocol/gmx:Anchor"
        protocol = self.get_single_xpath_value(xpath_prot)
        if not protocol in self.service_types:
            raise ValueError(
                f"md_id: {self.metadata_id}, unknown protocol found in gmd:CI_OnlineResource {protocol}")
        return self.service_types[protocol]

    def get_service_capabilities_url(self):
        xpath = f"{self.xpath_metadata}/gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource/gmd:linkage/gmd:URL"
        url = self.get_single_xpath_value(xpath)
        if not is_url(url):
            raise ValueError(
                f"md_id: {self.metadata_id}, no valid url found for gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource: {url}")
        return url

    def get_contact(self, base):
        xpath_organisationname = f"{base}/gmd:organisationName/gco:CharacterString"
        xpath_contact = f"{base}/gmd:contactInfo/gmd:CI_Contact"
        xpath_email = f"{xpath_contact}/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString"
        xpath_url = f"{xpath_contact}/gmd:onlineResource/gmd:CI_OnlineResource/gmd:linkage/gmd:URL"
        xpath_role = f"{base}/gmd:role/gmd:CI_RoleCode/@codeListValue"
        result = {}
        result["organisationname"] = self.get_single_xpath_value(
            xpath_organisationname)
        result["email"] = self.get_single_xpath_value(xpath_email)
        result["url"] = self.get_single_xpath_value(xpath_url)
        result["role"] = self.get_single_xpath_att(xpath_role)
        return result

    def get_mdidentifier(self):
        xpath = f"{self.xpath_metadata}/gmd:fileIdentifier/gco:CharacterString"
        return self.get_single_xpath_value(xpath)

    def get_resource_identifier(self):
        xpath = f"{self.xpath_resource_identification}/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gmx:Anchor"
        return self.get_single_xpath_value(xpath)

    def get_resource_identifier_href(self):
        xpath = f"{self.xpath_resource_identification}/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gmx:Anchor/@xlink:href"
        return self.get_single_xpath_att(xpath)

    def get_datestamp(self):
        xpath = f"{self.xpath_metadata}/gmd:dateStamp/gco:Date"
        return self.get_single_xpath_value(xpath)

    def get_metadatastandardname(self):
        xpath = f"{self.xpath_metadata}/gmd:metadataStandardName/gco:CharacterString"
        return self.get_single_xpath_value(xpath)

    def get_metadatastandardversion(self):
        xpath = f"{self.xpath_metadata}/gmd:metadataStandardVersion/gco:CharacterString"
        return self.get_single_xpath_value(xpath)

    def get_md_date(self, date_type):
        xpath = f"{self.xpath_resource_identification}/gmd:citation/gmd:CI_Citation/gmd:date/gmd:CI_Date/gmd:dateType/gmd:CI_DateTypeCode[@codeListValue='{date_type}']/../../gmd:date/gco:Date"
        return self.get_single_xpath_value(xpath)

    def get_abstract(self):
        xpath = f"{self.xpath_resource_identification}/gmd:abstract/gco:CharacterString"
        return self.get_single_xpath_value(xpath)

    def get_title(self):
        xpath = f"{self.xpath_resource_identification}/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString"
        return self.get_single_xpath_value(xpath)

    def get_keywords(self):
        result = self.etree.xpath(
            f'{self.xpath_resource_identification}/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/gco:CharacterString', namespaces=self.namespaces)
        keywords = []
        for keyword in result:
            keywords.append(keyword.text)
        return keywords

    def get_inspire_theme_url(self):
        xpath = f"{self.xpath_resource_identification}/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:thesaurusName/gmd:CI_Citation/\
            gmd:title/gmx:Anchor[@xlink:href='http://www.eionet.europa.eu/gemet/inspire_themes']/../../../../gmd:keyword/gmx:Anchor/@xlink:href"
        uri = self.get_single_xpath_att(xpath)
        if uri:
            uri = uri.replace("http://", "https://")
        return uri

    def get_uselimitations(self):
        xpath = f"{self.xpath_resource_identification}/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation/gco:CharacterString"
        return self.get_single_xpath_value(xpath)

    def get_license(self):
        xpath_12 = f"{self.xpath_resource_identification}/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gco:CharacterString"
        xpath_20 = f"{self.xpath_resource_identification}/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/gmx:Anchor"
        xpath_20_href = f"{xpath_20}/@xlink:href"

        # first try nl profiel 2.0
        result = {}
        xpath_result = self.etree.xpath(
            xpath_20_href, namespaces=self.namespaces)
        if xpath_result:
            result["url"] = xpath_result[0]
            result["description"] = self.get_single_xpath_value(xpath_20)
        else:
            # otherwise try nl profiel 1.2
            xpath_result = self.etree.xpath(
                xpath_12, namespaces=self.namespaces)
            if len(xpath_result) <= 1:
                raise ValueError(
                    f"md_id: {self.metadata_id}, unable to determine license from metadata, xpath: gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints/")
            result["description"] = xpath_result[0].text
            result["url"] = xpath_result[1].text
        # validate license url
        if not is_url(result["url"]):
            result["url"], result["description"] = result["description"], result["url"]
            if not is_url(result["url"]):
                url_val = result["url"]
                raise ValueError(
                    f"md_id: {self.metadata_id}, could not determine license url in gmd:MD_LegalConstraints, found {url_val}")
        return result

    def is_inspire(self):
        # record is considered inspire record if has inspire theme defined
        xpath = f"{self.xpath_resource_identification}/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:thesaurusName/gmd:CI_Citation/\
            gmd:title/gmx:Anchor[@xlink:href='http://www.eionet.europa.eu/gemet/inspire_themes']/../../../../gmd:keyword/gmx:Anchor/@xlink:href"
        uri = self.get_single_xpath_att(xpath)
        if uri:
            return True
        else:
            return False

    def validate_xml_form(self):
        result = ""
        try:
            parser = et.XMLParser()
            et.fromstring(self.xml_string, parser=parser)
        except IOError:
            result = "Invalid File"
        # check for XML syntax errors
        except et.XMLSyntaxError as err:
            result = "XML Syntax Error: {0}".format(err.msg)
        return result

    def schema_validation_errors(self):
        result = self.validate_xml_form()
        if result:
            return result
        schema_path = pkg_resources.resource_filename(__name__,
                                                      "data/schema/schemas.opengis.net/csw/2.0.2/profiles/apiso/1.0.0/apiso.xsd")
        with open(schema_path, 'rb') as xml_schema_file:
            schema_doc = et.XML(xml_schema_file.read(), base_url=schema_path)
            schema = et.XMLSchema(schema_doc)
            parser = et.XMLParser(
                ns_clean=True, recover=True, encoding='utf-8')
            xml_string = et.XML(self.xml_string, parser=parser)
            if not schema.validate(xml_string):
                for error in schema.error_log:
                    result += f"\n\terror: {error.message}, line: {error.line}, column {error.column}"
        return result

    def is_valid(self):
        if self.schema_validation_errors():
            return False
        return True

    def get_thumbnails(self):
        result = []
        xpath = f"{self.xpath_resource_identification}/gmd:graphicOverview/gmd:MD_BrowseGraphic"
        xpath_result = self.etree.xpath(xpath, namespaces=self.namespaces)
        for graphic in xpath_result:
            xpath_file = f"gmd:fileName/gco:CharacterString"
            xpath_description = f"gmd:fileDescription/gco:CharacterString"
            xpath_filetype = f"gmd:fileType/gco:CharacterString"
            graphic_result = {}
            graphic_result["file"] = self.get_single_xpath_value(
                xpath_file, graphic)
            graphic_result["description"] = self.get_single_xpath_value(
                xpath_description, graphic)
            graphic_result["filetype"] = self.get_single_xpath_value(
                xpath_filetype, graphic)
            result.append(graphic_result)
        return result

    def get_servicetype(self):
        xpath = f"{self.xpath_resource_identification}/srv:serviceType/gco:LocalName"
        return self.get_single_xpath_value(xpath)

    def get_recordtype(self):
        xpath = f"{self.xpath_record_type}"
        return self.get_single_xpath_value(xpath)

    def get_bbox(self):
        if self.record_type == "service":
            extent_ns = "srv"
        elif self.record_type == "dataset":
            extent_ns = "gmd"
        xpath = f"{self.xpath_resource_identification}/{extent_ns}:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox"
        result = {}
        xpath_west = f"{xpath}/gmd:westBoundLongitude/gco:Decimal"
        xpath_east = f"{xpath}/gmd:eastBoundLongitude/gco:Decimal"
        xpath_north = f"{xpath}/gmd:northBoundLatitude/gco:Decimal"
        xpath_south = f"{xpath}/gmd:southBoundLatitude/gco:Decimal"
        result["minx"] = self.get_single_xpath_value(xpath_west)
        result["maxx"] = self.get_single_xpath_value(xpath_east)
        result["maxy"] = self.get_single_xpath_value(xpath_north)
        result["miny"] = self.get_single_xpath_value(xpath_south)
        return result

    def get_operateson(self):
        xpath_operateson = f"{self.xpath_resource_identification}/srv:operatesOn"
        xpath_result = self.etree.xpath(
            xpath_operateson, namespaces=self.namespaces)
        result_list = []
        for operateson in xpath_result:
            result = {}
            xpath_uuidref = "@uuidref"
            xpath_href = "@xlink:href"
            dataset_source_identifier = self.get_single_xpath_att(
                xpath_uuidref, operateson)
            dataset_md_url = self.get_single_xpath_att(xpath_href, operateson)
            parsed = urlparse(dataset_md_url.lower())
            dataset_md_identifier = parse_qs(parsed.query)['id'][0]
            result["dataset_md_identifier"] = dataset_md_identifier
            result["dataset_source_identifier"] = dataset_source_identifier
            # TODO: raise WarningException and implement exception handling for this type of exception
            # if dataset_source_identifier == dataset_md_identifier:
            #     raise WarningError(
            #         f"md_id: {self.metadata_id}, invalid metadata content operateson @uuidref and id\
            #             from @xlink:href are equal, value: {dataset_source_identifier}")
            result_list.append(result)
        return result_list

    def get_service_dictionary(self):
        result = {}
        inspire = self.is_inspire()
        result["inspire"] = inspire
        if inspire:
            result["inspire_theme_uri"] = self.get_inspire_theme_url()
        ogc_service_type = self.get_ogc_servicetype()
        result["ogc_service_type"] = ogc_service_type
        result["service_capabilities_url"] = self.get_service_capabilities_url()
        result["md_standardname"] = self.get_metadatastandardname()
        result["md_standardversion"] = self.get_metadatastandardversion()
        result["md_identifier"] = self.get_mdidentifier()
        result["datestamp"] = self.get_datestamp()
        result["service_title"] = self.get_title()
        result["service_abstract"] = self.get_abstract()
        pub_date = self.get_md_date("publication")
        rev_date = self.get_md_date("revision")
        create_date = self.get_md_date("creation")
        if not (pub_date or rev_date or create_date):
            raise ValueError(
                f"md_id: {self.metadata_id}, at least one of publication, revision or creation date should be set")

        result["metadata_identifier"] = self.get_mdidentifier()
        result["resource_identifier"] = self.get_resource_identifier()
        result["resource_identifier_href"] = self.get_resource_identifier_href()
        result["title"] = self.get_title()
        result["abstract"] = self.get_abstract()
        result["bbox"] = self.get_bbox()
        result["keywords"] = self.get_keywords()
        result["uselimitations"] = self.get_uselimitations()
        result["license"] = self.get_license()
        result["thumbnails"] = self.get_thumbnails()

        result["metadata_contact"] = self.get_contact(
            f"{self.xpath_metadata}/gmd:contact/gmd:CI_ResponsibleParty")
        result["resource_contact"] = self.get_contact(
            f"{self.xpath_resource_identification}/gmd:pointOfContact/gmd:CI_ResponsibleParty")

        if pub_date:
            result["publication_date"] = pub_date
        if rev_date:
            result["revision_date"] = rev_date
        if create_date:
            result["creation_date"] = create_date
        result["datestamp"] = self.get_datestamp()

        result["service_type"] = self.get_servicetype()
        result["ogc_service_type"] = self.get_ogc_servicetype()
        result["service_capabilities_url"] = self.get_service_capabilities_url()
        result["linked_datasets"] = self.get_operateson()

        result["inspire"] = self.is_inspire()
        if result["inspire"]:
            result["inspire_theme_uri"] = self.get_inspire_theme_url()

        result["md_standardname"] = self.get_metadatastandardname()
        result["md_standardversion"] = self.get_metadatastandardversion()

        return result

    def get_dataset_dictionary(self):
        result = {}
        pub_date = self.get_md_date("publication")
        rev_date = self.get_md_date("revision")
        create_date = self.get_md_date("creation")
        if not (pub_date or rev_date or create_date):
            raise ValueError(
                f"md_id: {self.metadata_id}, at least one of publication, revision or creation date should be set")

        result["metadata_identifier"] = self.get_mdidentifier()
        result["resource_identifier"] = self.get_resource_identifier()
        result["resource_identifier_href"] = self.get_resource_identifier_href()

        result["title"] = self.get_title()
        result["abstract"] = self.get_abstract()
        result["bbox"] = self.get_bbox()
        result["keywords"] = self.get_keywords()
        result["uselimitations"] = self.get_uselimitations()
        result["license"] = self.get_license()
        result["thumbnails"] = self.get_thumbnails()

        result["metadata_contact"] = self.get_contact(
            f"{self.xpath_metadata}/gmd:contact/gmd:CI_ResponsibleParty")
        result["resource_contact"] = self.get_contact(
            f"{self.xpath_resource_identification}/gmd:pointOfContact/gmd:CI_ResponsibleParty")

        if pub_date:
            result["publication_date"] = pub_date
        if rev_date:
            result["revision_date"] = rev_date
        if create_date:
            result["creation_date"] = create_date
        result["datestamp"] = self.get_datestamp()

        result["ogc_service_type"] = self.get_ogc_servicetype()
        result["service_capabilities_url"] = self.get_service_capabilities_url()

        result["metadata_standardname"] = self.get_metadatastandardname()
        result["metadata_standardversion"] = self.get_metadatastandardversion()

        result["inspire"] = self.is_inspire()
        if result["inspire"]:
            result["inspire_theme_uri"] = self.get_inspire_theme_url()

        return result

    def convert_to_dictionary(self):
        if self.record_type == "service":
            return self.get_service_dictionary()
        elif self.record_type == "dataset":
            return self.get_dataset_dictionary()
