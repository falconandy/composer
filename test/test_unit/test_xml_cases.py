from collections import OrderedDict
from typing import Dict

import pytest

from composer.efile.xmlio import JsonTranslator

@pytest.fixture()
def translate() -> JsonTranslator:
    return JsonTranslator()

@pytest.mark.parametrize("namespace", ["irs", "xsd", "foo"])
def test_standard_node_with_content(translate: JsonTranslator, namespace: str):
    raw_xml: str = """
    <?xml version="1.0" encoding="utf-8"?>
    <{}:MyElement>Expected</{}:MyElement>
    """.format(namespace, namespace)
    expected: OrderedDict = OrderedDict([("MyElement", "Expected")])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_no_xml_version(translate: JsonTranslator):
    raw_xml: str = "<irs:MyElement>Expected</irs:MyElement>"
    expected: OrderedDict = OrderedDict([("MyElement", "Expected")])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_no_namespace(translate: JsonTranslator):
    raw_xml: str = "<MyElement>Expected</MyElement>"
    expected: OrderedDict = OrderedDict([("MyElement", "Expected")])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_empty(translate: JsonTranslator):
    raw_xml: str = "<MyElement></MyElement>"
    expected: OrderedDict = OrderedDict([("MyElement", None)])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_empty_node_with_attribute(translate: JsonTranslator):
    raw_xml: str = '<MyElement a="foo"></MyElement>'
    expected: OrderedDict = OrderedDict([
        ("MyElement@a", "foo"),
        ("MyElement", None)
    ])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_with_attribute_and_text(translate: JsonTranslator):
    raw_xml: str = '<MyElement a="foo">bar</MyElement>'
    expected: OrderedDict = OrderedDict([
        ("MyElement@a", "foo"),
        ("MyElement", "bar")
    ])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_with_child(translate: JsonTranslator):
    raw_xml: str = """
    <Outer>
        <Inner>Blah</Inner>
    </Outer>
    """
    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("Inner", "Blah")
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_with_child_and_attribute(translate: JsonTranslator):
    raw_xml: str = """
    <Outer a="foo">
        <Inner>Blah</Inner>
    </Outer>
    """
    expected: OrderedDict = OrderedDict([
        ("Outer@a", "foo"),
        ("Outer", OrderedDict([
            ("Inner", "Blah")
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_standard_node_with_child_and_text_raises(translate: JsonTranslator):
    """This is a weird case, but it could happen, so we need to account for it"""
    raw_xml: str = """
    <Outer>
        The fact that this is permitted in XML is incomprehensible
        <Inner>Blah</Inner>
    </Outer>
    """
    with pytest.raises(ValueError):
        translate(raw_xml)

@pytest.mark.parametrize("namespace", ["irs", "xsd", "foo"])
def test_compact_node(translate: JsonTranslator, namespace: str):
    raw_xml: str = """
    <?xml version="1.0" encoding="utf-8"?>
    <{}:MyElement/>
    """.format(namespace, namespace)
    expected: OrderedDict = OrderedDict([("MyElement", None)])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_compact_node_no_namespace(translate: JsonTranslator):
    raw_xml: str = "<MyElement/>"
    expected: OrderedDict = OrderedDict([("MyElement", None)])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_compact_node_two_attributes(translate: JsonTranslator):
    raw_xml: str = '<MyElement a="foo" b="bar" />'
    expected: OrderedDict = OrderedDict([
        ("MyElement@a", "foo"),
        ("MyElement@b", "bar"),
        ("MyElement", None)
    ])
    actual: Dict = translate(raw_xml)
    assert actual == expected

def test_repeated_node_containing_text(translate: JsonTranslator):
    raw_xml: str = """
    <Outer>
        <MyElement>a</MyElement>
        <MyElement>b</MyElement>
    </Outer>
    """

    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("MyElement", ["a", "b"])
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_repeated_node_containing_children(translate: JsonTranslator):
    raw_xml: str = """
    <Outer>
        <MyElement>
            <Inner>a</Inner>
        </MyElement>
        <MyElement>
            <Inner>b</Inner>
        </MyElement>
    </Outer>
    """

    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("MyElement", [
                OrderedDict([("Inner", "a")]),
                OrderedDict([("Inner", "b")]),
            ])
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_repeated_node_containing_attributes(translate: JsonTranslator):
    """Treat attributes on repeated elements as if they were nested elements"""
    raw_xml: str = """
    <Outer>
        <MyElement a="foo"/>
        <MyElement a="bar"/>
    </Outer>
    """

    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("MyElement", [
                OrderedDict([("@a", "foo")]),
                OrderedDict([("@a", "bar")]),
            ])
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_repeated_node_containing_attributes_and_children(translate: JsonTranslator):
    raw_xml: str = """
    <Outer>
        <MyElement a="foo">
            <a>1</a>
        </MyElement>
        <MyElement a="bar">
            <a>2</a>
        </MyElement>
    </Outer>
    """

    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("MyElement", [
                OrderedDict([
                    ("@a", "foo"),
                    ("a", "1")
                ]),
                OrderedDict([
                    ("@a", "bar"),
                    ("a", "2")
                ])
            ])
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_repeated_empty_nodes(translate: JsonTranslator):
    raw_xml: str = """
    <Outer>
        <MyElement/>
        <MyElement/>
        <MyElement/>
        <MyElement/>
    </Outer>
    """

    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("MyElement", [None] * 4)
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_repeated_node_different_namespaces(translate: JsonTranslator):
    raw_xml: str = """
    <Outer>
        <foo:MyElement>a</foo:MyElement>
        <bar:MyElement>b</bar:MyElement>
    </Outer>
    """

    expected: OrderedDict = OrderedDict([
        ("Outer", OrderedDict([
            ("MyElement", ["a", "b"])
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_nested_repeating(translate: JsonTranslator):
    raw_xml: str = """
    <Container>
        <OuterList>
            <SomeText>Tuesday</SomeText>
            <InnerList>
                <Fruit>apple</Fruit>
                <Color>red</Color>
            </InnerList>
            <InnerList>
                <Fruit>lemon</Fruit>
                <Color>yellow</Color>
            </InnerList>
        </OuterList>
        <OuterList>
            <SomeText>Friday</SomeText>
            <InnerList>
                <Fruit>plum</Fruit>
                <Color>purple</Color>
            </InnerList>
            <InnerList>
                <Fruit>lime</Fruit>
                <Color>green</Color>
            </InnerList>
        </OuterList>
    </Container>
    """

    expected: OrderedDict = OrderedDict([
        ("Container", OrderedDict([
            ("OuterList", [
                OrderedDict([
                    ("SomeText", "Tuesday"),
                    ("InnerList", [
                        OrderedDict([
                            ("Fruit", "apple"),
                            ("Color", "red")
                        ]),
                        OrderedDict([
                            ("Fruit", "lemon"),
                            ("Color", "yellow")
                        ]),
                    ])
                ]),
                OrderedDict([
                    ("SomeText", "Friday"),
                    ("InnerList", [
                        OrderedDict([
                            ("Fruit", "plum"),
                            ("Color", "purple")
                        ]),
                        OrderedDict([
                            ("Fruit", "lime"),
                            ("Color", "green")
                        ]),
                    ])
                ])
            ])
        ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_nested_repeating_with_attributes(translate: JsonTranslator):
    raw_xml: str = """
    <Container a="1">
        <OuterList b="2">
            <SomeText>Tuesday</SomeText>
            <InnerList c="3">
                <Fruit>apple</Fruit>
                <Color>red</Color>
            </InnerList>
            <InnerList d="4">
                <Fruit>lemon</Fruit>
                <Color e="5">yellow</Color>
            </InnerList>
        </OuterList>
        <OuterList>
            <SomeText>Friday</SomeText>
            <InnerList>
                <Fruit>plum</Fruit>
                <Color>purple</Color>
            </InnerList>
            <InnerList>
                <Fruit>lime</Fruit>
                <Color>green</Color>
            </InnerList>
        </OuterList>
    </Container>
    """

    expected: OrderedDict = OrderedDict([
        ("Container@a", "1"),
        ("Container", OrderedDict([
            ("OuterList", [
                OrderedDict([
                    ("@b", "2"),
                    ("SomeText", "Tuesday"),
                    ("InnerList", [
                        OrderedDict([
                            ("@c", "3"),
                            ("Fruit", "apple"),
                            ("Color", "red")
                        ]),
                        OrderedDict([
                            ("@d", "4"),
                            ("Fruit", "lemon"),
                            ("Color@e", "5"),
                            ("Color", "yellow")
                        ]),
                    ])
                ]),
                OrderedDict([
                    ("SomeText", "Friday"),
                    ("InnerList", [
                        OrderedDict([
                            ("Fruit", "plum"),
                            ("Color", "purple")
                        ]),
                        OrderedDict([
                            ("Fruit", "lime"),
                            ("Color", "green")
                        ]),
                    ])
                ])
            ])
        ])),
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual

def test_irs_boilerplate(translate: JsonTranslator):
    raw_xml: str = """
    <?xml version="1.0" encoding="utf-8"?>
    <Return xmlns="http://www.irs.gov/efile" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.irs.gov/efile" returnVersion="2010v3.2">
      <ReturnHeader binaryAttachmentCount="0">
        <Timestamp>2011-02-22T15:44:44-06:00</Timestamp>
        <TaxPeriodEndDate>2010-12-31</TaxPeriodEndDate>
        <PreparerFirm>
          <PreparerFirmBusinessName>
            <BusinessNameLine1>CUMMINGS LAMONT &amp;AMP MCNAMEE PA</BusinessNameLine1>
          </PreparerFirmBusinessName>
          <PreparerFirmUSAddress>
            <AddressLine1>305 LAFAYETTE CENTER</AddressLine1>
            <City>KENNEBUNK</City>
            <State>ME</State>
            <ZIPCode>04043</ZIPCode>
          </PreparerFirmUSAddress>
        </PreparerFirm>
      </ReturnHeader>
    </Return>
    """

    expected: OrderedDict = OrderedDict([
        ("Return@returnVersion", "2010v3.2"),
        ("Return", OrderedDict([
            ("ReturnHeader@binaryAttachmentCount", "0"),
            ("ReturnHeader", OrderedDict([
                ("Timestamp", "2011-02-22T15:44:44-06:00"),
                ("TaxPeriodEndDate", "2010-12-31"),
                ("PreparerFirm", OrderedDict([
                    ("PreparerFirmBusinessName", OrderedDict([
                        ("BusinessNameLine1", "CUMMINGS LAMONT &AMP MCNAMEE PA")
                    ])),
                    ("PreparerFirmUSAddress", OrderedDict([
                        ("AddressLine1", "305 LAFAYETTE CENTER"),
                        ("City", "KENNEBUNK"),
                        ("State", "ME"),
                        ("ZIPCode", "04043"),
                    ]))
                ]))
             ]))
         ]))
    ])
    actual: Dict = translate(raw_xml)
    assert expected == actual
