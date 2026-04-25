# Smart Wastebin — Custom Ontology Terms

Base namespace: `https://github.com/FanisSamaras/iotlab1_rasb1/blob/main/docs/ontology.md#`

Recommended prefix: `team`

This document defines only the custom terms currently used in `models/wastebin.jsonld`.

---

## Custom Classes

### WasteBin
- **Kind:** Class
- **IRI:** `team:WasteBin`
- **Description:** A physical wastebin monitored by the smart wastebin system.

---

## Custom Object Properties

### hasSensor
- **Kind:** Object Property
- **IRI:** `team:hasSensor`
- **Applies to:** `team:WasteBin`
- **Value type:** `sosa:Sensor`
- **Description:** Links a wastebin to a sensor mounted on or assigned to it.

### locatedIn
- **Kind:** Object Property
- **IRI:** `team:locatedIn`
- **Applies to:** `team:WasteBin`
- **Value type:** `bot:Space`
- **Description:** Indicates the environment in which the wastebin is deployed.

### deployment
- **Kind:** Object Property
- **IRI:** `team:deployment`
- **Applies to:** `sosa:Sensor`
- **Subclasses:** `team:deployment:mountedOn`,`team:deployment:deployedIN`
- **Value type(of subclasses):** `mountedOn:team:WasteBin`,`deployedIn:schema:place`

### status
- **Kind:** Object Property
- **IRI:** `team:deployment`
- **Applies to:** `sosa:Sensor`
- **Subclasses:** `team:status:currentStatus`,`team:status:installationDate`
- **Value type(of subclasses):** `currentStatus:xsd:string`,`installationDate:xsd:dateTime`

---

## Custom Datatype Properties

### capacityLiters
- **Kind:** Datatype Property
- **IRI:** `team:capacityLiters`
- **Applies to:** `team:WasteBin`
- **Type:** `xsd:integer`
- **Description:** Nominal capacity of the wastebin in liters.

### wasteType
- **Kind:** Datatype Property
- **IRI:** `team:wasteType`
- **Applies to:** `team:WasteBin`
- **Type:** `xsd:string`
- **Description:** The type of waste accepted by the bin, such as `mixed`, `paper`, or `recyclable`.

### collectionZone
- **Kind:** Datatype Property
- **IRI:** `team:collectionZone`
- **Applies to:** `team:WasteBin`
- **Type:** `xsd:string`
- **Description:** Operational collection zone used for organizing waste collection.

### currentStatus
- **Kind:** Datatype Property
- **IRI:** `team:currentStatus`
- **Applies to:** `team:WasteBin`
- **Type:** `xsd:string`
- **Description:** Current operational state of the wastebin, such as `active`, `full`, or `maintenance`.

### heightCm
- **Kind:** Datatype Property
- **IRI:** `team:heightCm`
- **Applies to:** `team:WasteBin`
- **Type:** `xsd:decimal`
- **Description:** Height of the wastebin in centimeters.

### diameterCm
- **Kind:** Datatype Property
- **IRI:** `team:diameterCm`
- **Applies to:** `team:WasteBin`
- **Type:** `xsd:decimal`
- **Description:** Diameter of the wastebin in centimeters.