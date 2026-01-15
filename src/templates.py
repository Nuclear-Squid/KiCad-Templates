from hierarchical_object import HierarchicalObject


class SCH_Templates:
    
    CAN_BUFFER = HierarchicalObject(
    sheet_name = "CANBuffer",
    sheet_file="subsystems/can_buffer.kicad_sch",
    at_xy=[0,0],
    size_wh=[30,20],
    properties={"Comment": "CAN Buffer"},
    pins=[
        {"name": "CAN_H", "type": "bidirectional", "net": "CAN_H"},
        {"name": "CAN_L", "type": "bidirectional", "net": "CAN_L"},
        {"name": "CAN_TX", "type": "bidirectional", "net": "CAN_TX"},
        {"name": "CAN_RX", "type": "bidirectional", "net": "CAN_RX"},
    ])

    CAPT_TEMP = HierarchicalObject(
        sheet_name = "TempSensor",
        sheet_file="subsystems/capt_temp.kicad_sch",
        at_xy=[0,0],
        size_wh=[30,20],
        properties={"Comment": "Temperature Sensor"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
        ]
    )

    BME680 = HierarchicalObject(
        sheet_name = "BME680",
        sheet_file="subsystems/s_bme680.kicad_sch",
        at_xy=[0,0],
        size_wh=[30,20],
        properties={"Comment": "Temperature Sensor"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
        ]
    )

    ACC_MAG = HierarchicalObject(
        sheet_name = "ACC_MAG",
        sheet_file="subsystems/acc_mag.kicad_sch",
        at_xy=[0,0],
        size_wh=[30,20],
        properties={"Comment": "Accelerometer and Magnetometer"},
        pins=[
            {"name": "SDA", "type": "bidirectional", "net": "SDA"},
            {"name": "SCL", "type": "bidirectional", "net": "SCL"},
            {"name": "INT_MAG", "type": "input", "net": "INT_MAG"},
        ]
    )

    MIKROBUS = HierarchicalObject(
        sheet_name = "MIKROBUS",
        sheet_file="subsystems/mikrobus.kicad_sch",
        at_xy=[0,0],
        size_wh=[30,20],
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