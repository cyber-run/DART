## Supported G-code commands for Theia SCF4 Controller

| Category                       | Command | Description                                | Returns                          |
|--------------------------------|---------|--------------------------------------------|----------------------------------|
| **Version strings and identification commands** ||||
| -                              | $S      | Return version, SN, model, and brand strings | See details below              |
| **Controller initialization**  ||||
| -                              | $B1     | Reset motor driver                         | OK                               |
| -                              | $B2     | Reset and initialize motor driver          | OK                               |
| -                              | $B3     | Reset STM32F103 processor                  | OK                               |
| **Motion commands**            ||||
| -                              | G0      | Rapid positioning                          | OK                               |
| -                              | G4      | Wait / stall after complete                | OK                               |
| -                              | G90     | Absolute programming mode                  | OK                               |
| -                              | G91     | Incremental programming mode               | OK                               |
| -                              | G92     | Set position                               | OK                               |
| **Miscellaneous function**     ||||
| -                              | M0      | Compulsory stop                            | OK                               |
| -                              | M7      | DN function with filter (VIS)              | OK                               |
| -                              | M8      | DN function no filter (IR + VIS)           | OK                               |
| -                              | M230    | Set normal move                            | OK                               |
| -                              | M231    | Set normal + forced move                   | OK                               |
| -                              | M232    | Set PI low/high detection voltage          | OK                               |
| -                              | M234    | Set motor and DN drive current             | OK                               |
| -                              | M235    | Set motor idle current                     | OK                               |
| -                              | M238    | PI LED on (some lenses leak light into sensor) | OK                           |
| -                              | M239    | PI LED off                                 | OK                               |
| -                              | M240    | Set motor drive speed                      | OK                               |
| -                              | M245    | Drive AUX output to low (high resistance output) | OK                          |
| -                              | M246    | Drive AUX output to high (low resistance output) | OK                          |
| -                              | M247    | Read power supply voltage value            | ADC=xxxx                         |
| **Advanced function**          ||||
| -                              | M241    | Dividing setting 1                         | OK                               |
| -                              | M242    | Pulse generation control 1                 | OK                               |
| -                              | M243    | Microstepping                              | OK                               |
| -                              | M244    | Dividing setting 2                         | OK                               |
| **Status commands**            ||||
| -                              | !1      | Return motor position, limit switch, moving status | 4000, 20000, 0, 0, 0, 0, 0, 0 |
