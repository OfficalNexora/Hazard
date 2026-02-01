import os

WSDL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wsdl")
if not os.path.exists(WSDL_DIR):
    os.makedirs(WSDL_DIR)

# 1. xmlmime.xsd
xmlmime_content = """<?xml version="1.0" ?>
<xs:schema targetNamespace="http://www.w3.org/2005/05/xmlmime"
   xmlns:xs="http://www.w3.org/2001/XMLSchema"
   xmlns:xmime="http://www.w3.org/2005/05/xmlmime" >
  <xs:attribute name="contentType">
    <xs:simpleType>
      <xs:restriction base="xs:string" >
        <xs:minLength value="3" />
      </xs:restriction>
    </xs:simpleType>
  </xs:attribute>
  <xs:attribute name="expectedContentTypes" type="xs:string" />
  <xs:complexType name="base64Binary">
    <xs:simpleContent>
        <xs:extension base="xs:base64Binary">
            <xs:attribute ref="xmime:contentType" />
        </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  <xs:complexType name="hexBinary">
    <xs:simpleContent>
        <xs:extension base="xs:hexBinary">
            <xs:attribute ref="xmime:contentType" />
        </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
</xs:schema>"""

with open(os.path.join(WSDL_DIR, "xmlmime.xsd"), "w") as f:
    f.write(xmlmime_content)
with open(os.path.join(WSDL_DIR, "xmlmime"), "w") as f:
    f.write(xmlmime_content)

# 2. xop-include.xsd
xop_content = """<?xml version="1.0" ?>
<xs:schema headers="yes" targetNamespace="http://www.w3.org/2004/08/xop/include" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:xop="http://www.w3.org/2004/08/xop/include">
  <xs:element name="Include" type="xop:Include"/>
  <xs:complexType name="Include">
    <xs:sequence>
      <xs:any maxOccurs="unbounded" minOccurs="0" namespace="##any" processContents="lax"/>
    </xs:sequence>
    <xs:attribute name="href" type="xs:anyURI" use="required"/>
    <xs:anyAttribute namespace="##other" processContents="lax"/>
  </xs:complexType>
</xs:schema>"""

with open(os.path.join(WSDL_DIR, "xop-include.xsd"), "w") as f:
    f.write(xop_content)
with open(os.path.join(WSDL_DIR, "xop"), "w") as f:
    f.write(xop_content)
with open(os.path.join(WSDL_DIR, "include"), "w") as f:
    f.write(xop_content)

# 3. envelope
envelope_content = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           xmlns:tns="http://schemas.xmlsoap.org/soap/envelope/"
           targetNamespace="http://schemas.xmlsoap.org/soap/envelope/" >

  <xs:element name="Envelope" type="tns:Envelope"/>
  <xs:complexType name="Envelope">
    <xs:sequence>
      <xs:element ref="tns:Header" minOccurs="0"/>
      <xs:element ref="tns:Body" minOccurs="1"/>
      <xs:any namespace="##other" minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
    <xs:anyAttribute namespace="##other" processContents="lax"/>
  </xs:complexType>

  <xs:element name="Header" type="tns:Header"/>
  <xs:complexType name="Header">
    <xs:sequence>
      <xs:any namespace="##other" minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
    <xs:anyAttribute namespace="##other" processContents="lax"/>
  </xs:complexType>

  <xs:element name="Body" type="tns:Body"/>
  <xs:complexType name="Body">
    <xs:sequence>
        <xs:any namespace="##any" minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
    <xs:anyAttribute namespace="##other" processContents="lax"/>
  </xs:complexType>

   <xs:element name="Fault" type="tns:Fault"/>
   <xs:complexType name="Fault">
    <xs:sequence>
      <xs:element name="faultcode" type="xs:QName"/>
      <xs:element name="faultstring" type="xs:string"/>
      <xs:element name="faultactor" type="xs:anyURI" minOccurs="0"/>
      <xs:element name="detail" type="tns:detail" minOccurs="0"/>
    </xs:sequence>
  </xs:complexType>

  <xs:complexType name="detail">
    <xs:sequence>
      <xs:any namespace="##any" minOccurs="0" maxOccurs="unbounded" processContents="lax"/>
    </xs:sequence>
    <xs:anyAttribute namespace="##other" processContents="lax"/>
  </xs:complexType>
</xs:schema>"""

with open(os.path.join(WSDL_DIR, "envelope"), "w") as f:
    f.write(envelope_content)

print("Created xmlmime, xop, and envelope files.")
