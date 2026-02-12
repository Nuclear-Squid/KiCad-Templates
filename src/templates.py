from pathlib import Path

from hierarchical_object import HierarchicalObject

PROJECT_FOLDER = Path(__file__).parent.parent
SUBSYSTEM_FOLDER = PROJECT_FOLDER / 'subsystems'



class SCH_Templates:

    CAN_BUFFER = HierarchicalObject(
        sheet_name="CANBuffer",
        sheet_file=SUBSYSTEM_FOLDER / "can_buffer.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "CAN Buffer"},
        pins=[
            {"name": "CAN_H", "type": "bidirectional", "net": "CAN_H"},
            {"name": "CAN_L", "type": "bidirectional", "net": "CAN_L"},
            {"name": "CAN_TX", "type": "bidirectional", "net": "CAN_TX"},
            {"name": "CAN_RX", "type": "bidirectional", "net": "CAN_RX"},
        ])

    CAPT_TEMP = HierarchicalObject(
        sheet_name="TempSensor",
        sheet_file=SUBSYSTEM_FOLDER / "capt_temp.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "Temperature Sensor"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
        ]
    )

    BME680 = HierarchicalObject(
        sheet_name="BME680",
        sheet_file=SUBSYSTEM_FOLDER / "s_bme680.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "Temperature Sensor"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
        ]
    )

    ACC_MAG = HierarchicalObject(
        sheet_name="ACC_MAG",
        sheet_file=SUBSYSTEM_FOLDER / "acc_mag.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "Accelerometer and Magnetometer"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
            {"name": "INT_MAG", "type": "input", "net": "INT_MAG"},
        ]
    )

    MIKROBUS = HierarchicalObject(
        sheet_name="MIKROBUS",
        sheet_file=SUBSYSTEM_FOLDER / "mikrobus.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "MikroBUS Interface"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
            {"name": "INT", "type": "input", "net": "INT_MK"},
            {"name": "RESET", "type": "input", "net": "RESET_MK"},
            {"name": "CS", "type": "bidirectional", "net": "CS_MK"},
            {"name": "SCK", "type": "bidirectional", "net": "SCK"},
            {"name": "MOSI", "type": "bidirectional", "net": "MOSI"},
            {"name": "MISO", "type": "bidirectional", "net": "MISO"},
            {"name": "PWM", "type": "bidirectional", "net": "PWM_MK"},
            {"name": "RX", "type": "bidirectional", "net": "RX_MK"},
            {"name": "TX", "type": "bidirectional", "net": "TX_MK"},
        ]
    )

    I2C_PERIPHERALS = HierarchicalObject(
        sheet_name="I2C_Peripherals",
        sheet_file=SUBSYSTEM_FOLDER / "i2c_peripherals.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "I2C Peripherals"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
        ]
    )

    ADC_ADS1115 = HierarchicalObject(
        sheet_name="ADC_ADS1115",
        sheet_file=SUBSYSTEM_FOLDER / "adc_ads1115.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "ADC ADS1115"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
        ]
    )

    BUZZER = HierarchicalObject(
        sheet_name="BUZZER",
        sheet_file=SUBSYSTEM_FOLDER / "buzzer.kicad_sch",
        at_xy=[0, 0],
        size_wh=[30, 20],
        properties={"Comment": "Buzzer"},
        pins=[
            {"name": "BUZZER_PIN", "type": "input", "net": "BUZZER"},
        ]
    )

    @classmethod
    def find_sheet_folder(cls, folder_name: str) -> HierarchicalObject | None:
        known_templates = [
            cls.CAN_BUFFER,
            cls.CAPT_TEMP,
            cls.BME680,
            cls.ACC_MAG,
            cls.MIKROBUS,
            cls.I2C_PERIPHERALS,
        ]

        for template in known_templates:
            if template.sheet_file == f"subsystems/{folder_name}/{folder_name}.kicad_sch":
                return template
        return None
