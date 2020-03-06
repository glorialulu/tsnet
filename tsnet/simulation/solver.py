"""
The tsnet.simulation.solver module contains methods to solver MOC
for different grid configurations, including:
1. inner_node
2. valve_node
3. pump_node
4. source_pump
5. valve_end
6. dead_end
7. rev_end
8. add_leakage

"""
from __future__ import print_function
import numpy as np
import warnings
def Reynold(V, D):
    """ Calculate Reynold number

    Parameters
    ----------
    V : float
        velocity
    D : float
        diameter

    Returns
    -------
    Re : float
        Reynold number
    """
    nu = 1.004e-6  # kinematic viscosity [m^2/s]
    Re = np.abs(V*D/nu)

    return Re

def quasi_steady_friction_factor(Re, KD):
    """ Update friction factor based on Reynold number

    Parameters
    ----------
    Re : float
        velocity
    KD : float
        relative roughness height (K/D)

    Returns
    -------
    f : float
        quasi-steady friction factor
    """
    a = -1.8*np.log10(6.9/Re +KD)
    f = (1/a)**2.
    return f


def unsteady_friction(Re, dVdt, dVdx, V, a, g):
    """ Calculate unsteady friction

    Parameters
    ----------
    Re : float
        velocity
    dVdt : float
        local instantaneous acceleration
    dVdx : float
        instantaneous convective acceleration
    V : float
        velocity
    a : float
        wave speed
    g: float
        gravitational acceleration

    Returns
    -------
    Ju : float
        unsteady friction factor
    """

    # calculate Vardy's shear decay coefficient (C)
    if Re< 2000: # laminar flow
        C = 4.76e-3
    else:
        C = 7.41 / Re**(np.log10(14.3/Re**0.05))

    # calculate Brunone's friction coefficient
    k = np.sqrt(C)/2.

    Ju = k/g/2.* (dVdt + a* np.sign(V) * np.abs(dVdx))
    return Ju

def cal_friction(friction, f, D, V, KD, dt, dVdt, dVdx, a, g ):
    """ Calculate friction term

    Parameters
    ----------
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    f : float
        steady friction factor
    D : float
        pipe diameter
    V : float
        pipe flow velocity
    KD : float
        relative roughness height
    dt : float
        time step
    dVdt : float
        local instantaneous acceleration
    dVdx : float
        convective instantaneous acceleration
    a : float
        wave speed
    g : float
        gravitational accelerations

    Returns
    -------
    float
        total friction, including steady and unsteady
    """

    if friction == 'steady':
        Ju = 0
        Js = f*dt/2./D*V*abs(V) #steady friction
    else:
        Re = Reynold(V, D)
        if Re!=0:
            f = quasi_steady_friction_factor(Re, KD)
        Js = f*dt/2./D*V*abs(V)
        if friction == 'quasi-steady':
            Ju = 0
        elif friction == 'unsteady':
            " TO DO: check the sign of unsteady friction"
            Ju = unsteady_friction(Re, dVdt, dVdx, V, a, g)
    return Ju + Js

def cal_Cs( link1, link2, H1, V1, H2, V2, s1, s2, g, dt,
            friction, dVdx1, dVdx2, dVdt1, dVdt2):
    """Calculate coefficients for MOC characteristic lines

    Parameters
    ----------
    link1 : object
        Pipe object of C+ charateristics curve
    link2 : object
        Pipe object of C- charateristics curve
    H1 : list
        List of the head of C+ charateristics curve
    V1 : list
        List of the velocity of C+ charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    s1 : list
        List of signs that represent the direction of the flow
        in C+ charateristics curve
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve

    Returns
    -------
    A1: list
        list of left adjacent pipe cross-section area
    A2: list
        list of right adjacent pipe cross-section area
    C1: list
        list of left adjacent pipe MOC coefficients
    C2: list
        list of right adjacent pipe MOC coefficients
    """

    # property of left adjacent pipe
    f1 = [link1[i].roughness  for i in range(len(link1))]       # unitless
    D1 = [link1[i].diameter  for i in range(len(link1))]        # m
    a1 = [link1[i].wavev  for i in range(len(link1))]           # m/s
    A1 = [np.pi * D1[i]**2. / 4.  for i in range(len(link1))]   # m^2
    C1 = np.zeros((len(link1),2), dtype=np.float64)
    theta1 = [link1[i].theta for i in range((len(link1)))]
    KD1 = [link1[i].roughness_height  for i in range(len(link1))]

    for i in range(len(link1)):
        J = cal_friction(friction, f1[i], D1[i], V1[i], KD1[i],
            dt, dVdt1[i], dVdx1[i], a1[i], g )
        C1[i,0] = s1[i]*V1[i] + g/a1[i]*H1[i] - s1[i]*J + g/a1[i]* dt *V1[i]*theta1[i]
        C1[i,1] = g/a1[i]

    # property of right adjacent pipe
    f2 = [link2[i].roughness  for i in range(len(link2))]      # unitless
    D2 = [link2[i].diameter  for i in range(len(link2))]       # m
    a2 = [link2[i].wavev  for i in range(len(link2))]          # m/s
    A2 = [np.pi * D2[i]**2. / 4.  for i in range(len(link2))]  # m^2
    C2 = np.zeros((len(link2),2),dtype=np.float64)
    theta2 = [link2[i].theta for i in range((len(link2)))]
    KD2 = [link2[i].roughness_height  for i in range(len(link2))]

    for i in range(len(link2)):
        J = cal_friction(friction, f2[i], D2[i], V2[i], KD2[i],
            dt, dVdt2[i], dVdx2[i], a2[i], g)
        C2[i,0] = s2[i]*V2[i] + g/a2[i]*H2[i] - s2[i]* J + g/a2[i]* dt *V2[i]*theta2[i]
        C2[i,1] = g/a2[i]

    return A1, A2, C1, C2



def inner_node(link1, link2, demand, H1, V1, H2, V2, dt, g, nn, s1, s2,
                friction, dVdx1, dVdx2, dVdt1, dVdt2):
    """Inner boundary MOC using C+ and C- characteristic curve

    Parameters
    ----------
    link1 : object
        Pipe object of C+ charateristics curve
    link2 : object
        Pipe object of C- charateristics curve
    demand : float
        demand at the junction
    H1 : list
        List of the head of C+ charateristics curve
    V1 : list
        List of the velocity of C+ charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    nn : int
        The index of the calculation node
    s1 : list
        List of signs that represent the direction of the flow
        in C+ charateristics curve
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    Returns
    -------
    HP : float
        Head at current node at current time
    VP : float
        Velocity at current node at current time
    """

    try :
        list(link1)
    except:
        link1 = [link1]
        V1 = [V1] ; H1 = [H1]
        dVdx1 = [dVdx1]; dVdt1 = [dVdt1]
    try :
        list(link2)
    except:
        link2 = [link2]
        V2 = [V2] ; H2 = [H2]
        dVdx2 = [dVdx2]; dVdt2 = [dVdt2]

    A1, A2, C1, C2 = cal_Cs(link1, link2, H1, V1, H2, V2, s1, s2, g, dt,
            friction, dVdx1, dVdx2, dVdt1, dVdt2)

    if link1 == link2 : # inner node of one pipe
        HP = ((np.dot(C1[:,0], A1) + np.dot(C2[:,0],A2)) /
         (np.dot(C1[:,1], A1) + np.dot(C2[:,1],A2)))

    else : # junction
        HP = (((np.dot(C1[:,0], A1) + np.dot(C2[:,0],A2)) - demand)/
         (np.dot(C1[:,1], A1) + np.dot(C2[:,1],A2)))
    if nn == 0:  # pipe start
        VP = np.float64(-C2[:,0]+ C2[:,1]*HP)
    else:        # pipe end
        VP = np.float64(C1[:,0] - C1[:,1]*HP)
    return HP, VP


def valve_node(KL_inv, link1, link2, H1, V1, H2, V2, dt, g, nn, s1, s2,
                friction, dVdx1, dVdx2, dVdt1, dVdt2):
    """Inline valve node MOC calculation

    Parameters
    ----------
    KL_inv : int
        Inverse of the valve loss coefficient at current time
    link1 : object
        Pipe object of C+ charateristics curve
    link2 : object
        Pipe object of C- charateristics curve
    H1 : list
        List of the head of C+ charateristics curve
    V1 : list
        List of the velocity of C+ charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    nn : int
        The index of the calculation node
    s1 : list
        List of signs that represent the direction of the flow
        in C+ charateristics curve
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """

    try :
        list(link1)
    except:
        link1 = [link1]
        V1 = [V1] ; H1 = [H1]
        dVdx1 = [dVdx1]; dVdt1 = [dVdt1]

    try :
        list(link2)
    except:
        link2 = [link2]
        V2 = [V2] ; H2 = [H2]
        dVdx2 = [dVdx2]; dVdt2 = [dVdt2]

    A1, A2, C1, C2 = cal_Cs(link1, link2, H1, V1, H2, V2, s1, s2, g, dt,
            friction, dVdx1, dVdx2, dVdt1, dVdt2)

    # parameters of the quadratic polynomial
    aq = 1
    bq = 2*g*KL_inv* (A2[0]/A1[0]/C1[0,1] + 1/C2[0,1])
    cq = 2*g*KL_inv* (C2[0,0]/C2[0,1] - C1[0,0]/C1[0,1])

    # solve the quadratic equation
    delta = bq**2 - 4*aq*cq

    if delta >= 0:
        VP = (-bq + np.sqrt(delta))/(2*aq)
    elif delta > -1.0e-7 and delta <0 :
        VP = (-bq)/(2*aq)
    else:
        VP = (-bq)/(2*aq)
        warnings.warn('Error: The quadratic equation has no real solution (valve)')

    if VP >=0 : # positive flow
        if nn == 0:  # pipe start
            VP = VP
            HP = (C2[0,0] + VP) / C2[0,1]
        else:        # pipe end
            VP = VP*A2[0]/A1[0]
            HP = (C1[0,0] - VP) / C1[0,1]

    else : # reverse flow
        # reconstruct the quadratic equation
        # parameters of the quadratic polynomial
        aq = 1
        bq = 2*g*KL_inv* (-A1[0]/A2[0]/C2[0,1]-1/C1[0,1])
        cq = 2*g*KL_inv* (-C2[0,0]/C2[0,1]+C1[0,0]/C1[0,1])

        # solve the quadratic equation
        delta = bq**2 - 4*aq*cq

        if delta >= 0:
            VP = (-bq - np.sqrt(delta))/(2*aq)
        elif delta > -1.0e-7 and delta <0 :
            VP = (-bq)/(2*aq)
        else:
            VP = (-bq)/(2*aq)
            warnings.warn('Error: The quadratic equation has no real solution (valve)')

        if nn == 0:  # pipe start
            VP = VP*A1[0]/A2[0]
            HP = (C2[0,0] + VP ) / C2[0,1]
        else:        # pipe end
            VP = VP
            HP = (C1[0,0] - VP) / C1[0,1]
    return HP, VP


def pump_node(pumpc,link1, link2, H1, V1, H2, V2, dt, g, nn, s1, s2,
                friction, dVdx1, dVdx2, dVdt1, dVdt2):
    """ Inline pump node MOC calculation

    Parameters
    ----------
    pumpc : list
        Parameters (a, b,c) to define pump characteristic cure,
        so that
        .. math:: h_p = a*Q**2 + b*Q + c
    link1 : object
        Pipe object of C+ charateristics curve
    link2 : object
        Pipe object of C- charateristics curve
    H1 : list
        List of the head of C+ charateristics curve
    V1 : list
        List of the velocity of C+ charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    nn : int
        The index of the calculation node
    s1 : list
        List of signs that represent the direction of the flow
        in C+ charateristics curve
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """

    try :
        list(link1)
    except:
        link1 = [link1]
        V1 = [V1] ; H1 = [H1]
        dVdx1 = [dVdx1]; dVdt1 = [dVdt1]

    try :
        list(link2)
    except:
        link2 = [link2]
        V2 = [V2] ; H2 = [H2]
        dVdx2 = [dVdx2]; dVdt2 = [dVdt2]

    A1, A2, C1, C2 = cal_Cs( link1, link2, H1, V1, H2, V2, s1, s2, g, dt,
            friction, dVdx1, dVdx2, dVdt1, dVdt2)

    # pump power function
    ap, bp, cp = pumpc[0]
    ap = ap * A1[0]**2.
    bp = bp * A1[0]

    # parameters of the quadratic polynomial
    aq = 1
    bq = 1/ap * (bp - 1/C1[0,1] - A1[0]/C2[0,1]/A2[0])
    cq = 1/ap * (-C2[0,0]/C2[0,1] + C1[0,0]/C1[0,1] + cp)

    # solve the quadratic equation
    delta = bq**2. - 4.*aq*cq
    if delta >= 0:
        VP = (-bq + np.sqrt(delta))/(2*aq)
    elif delta > -1.0e-7 and delta <0 :
        VP = (-bq)/(2*aq)
    else:
        VP = (-bq)/(2*aq)
        warnings.warn('Error: The quadratic equation has no real solution (pump)')

    hp = ap*VP**2. + bp*VP + cp # head gain

    if VP > 0 and hp >=0 : # positive flow & positive head gain
        if nn == 0:  # pipe start
            VP = VP*A1[0]/A2[0]
            HP = (C2[0,0] + VP ) / C2[0,1]
        else:        # pipe end
            VP = VP
            HP = (C1[0,0] - VP) / C1[0,1]
    elif VP<0 :
        warnings.warn( "Reverse flow stopped by check valve!")
        VP = 0
        hp = cp
        # suction or discharge side?
        if pumpc[1] == "s": # suction side
            if nn == 0:  # pipe start
                HP = (C2[0,0] + VP ) / C2[0,1]
            else :
                HP = (C1[0,0] - VP) / C1[0,1]
        else: #discharge
            if nn == 0:  # pipe start
                HP = (C1[0,0] - VP) / C1[0,1] + hp
            else :
                HP = (C2[0,0] + VP ) / C2[0,1] + hp
    else: # positive flow and negative head gain
        warnings.warn( "Negative head gain activates by-pass!")
        hp = 0
        # suction or discharge side?
        if pumpc[1] == "s": # suction side
            if nn == 0:  # pipe start
                HP = (C2[0,0] + VP ) / C2[0,1]
            else :
                HP = (C1[0,0] - VP) / C1[0,1]
        else:
            if nn == 0:  # pipe start
                HP = (C1[0,0] - VP) / C1[0,1] + hp
            else :
                HP = (C2[0,0] + VP ) / C2[0,1] +hp


    return HP, VP

def source_pump(pump, link2, H2, V2, dt, g, s2,
                friction, dVdx2, dVdt2):
    """Source Pump boundary MOC calculation

    Parameters
    ----------
    pump : list
        pump[0]: elevation of the reservoir/tank
        pump[1]: Parameters (a, b,c) to define pump characteristic cure,
        so that
        .. math:: h_p = a*Q**2 + b*Q + c
    link2 : object
        Pipe object of C- charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """
    pumpc = pump[1]
    Hsump = pump[0]
    try :
        list(link2)
    except:
        link2 = [link2]
        V2 = [V2] ; H2 = [H2]
        dVdx2 = [dVdx2]; dVdt2 = [dVdt2]

    _, A2, _, C2 = cal_Cs( link2, link2, H2, V2, H2, V2, s2, s2, g, dt,
            friction, dVdx2, dVdx2, dVdt2, dVdt2)

    # pump power function
    ap, bp, cp = pumpc
    ap = ap * A2[0]**2.
    bp = bp * A2[0]

    # parameters of the quadratic polynomial
    aq = ap * C2[0,1]**2.
    bq = bp*C2[0,1] - 2.*ap*C2[0,0]*C2[0,1] - 1
    cq = ap*C2[0,0]**2. - bp*C2[0,0] + Hsump + cp

    # solve the quadratic equation
    delta = bq**2. - 4.*aq*cq
    if delta >= 0:
        HP = (-bq - np.sqrt(delta))/(2*aq)
    elif delta > -1.0e-7 and delta <0 :
        HP = (-bq)/(2*aq)
    else:
        HP = (-bq)/(2*aq)
        warnings.warn('The quadratic equation has no real solution (pump)')

    if HP > Hsump:
        VP = np.float64(-C2[0,0] + C2[0,1]*HP)
    else :
        HP = Hsump
        VP = np.float64(-C2[0,0] + C2[0,1]*HP)

    if VP <= 0 : # positive flow
        warnings.warn( "Reverse flow stopped by check valve!")
        VP = 0
        HP = (C2[0,0] + VP ) / C2[0,1]

    return HP, VP



def valve_end(H1, V1, V, nn, a, g, f, D, dt,
             KD, friction, dVdx2, dVdt2):
    """ End Valve boundary MOC calculation

    Parameters
    ----------
    H1 : float
        Head of the C+ charateristics curve
    V1 : float
        Velocity of the C+ charateristics curve
    V : float
        Velocity at the valve end at current time
    nn : int
        The index of the calculation node
    a : float
        Wave speed at the valve end
    g : float
        Gravity acceleration
    f : float
        friction factor of the current pipe
    D : float
        diameter of the current pipe
    dt : float
        Time step
    KD : float
        relative roughness height
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """
    J = cal_friction(friction, f, D, V, KD, dt, dVdt2, dVdx2, a, g )
    if nn == 0 :
        # HP = H1 + a/g*(V - V1) + a/g*f*dt/(2.*D)*V1*abs(V1)
        HP = H1 + a/g*(V - V1) + a/g*J
        VP = V
    else :
        HP = H1 - a/g*(V - V1) - a/g*J
        VP = V
    return HP,VP

def dead_end(linkp, H1, V1, elev, nn, a, g, f, D, dt,
            KD, friction, dVdx1, dVdt1):
    """Dead end boundary MOC calculation with pressure dependant demand

    Parameters
    ----------
    linkp : object
        Current pipe
    H1 : float
        Head of the C+ charateristics curve
    V1 : float
        Velocity of the C+ charateristics curve
    elev : float
        Elevation at the dead end node
    nn : int
        The index of the calculation node
    a : float
        Wave speed at the valve end
    g : float
        Gravity acceleration
    f : float
        friction factor of the current pipe
    D : float
        diameter of the current pipe
    dt : float
        Time step
    KD : float
        relative roughness height
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    """

    A = np.pi/4. * linkp.diameter**2.
    J = cal_friction(friction, f, D, V1, KD, dt, dVdt1, dVdx1, a, g )
    if nn == 0: # dead end is the start node of a pipe
        k = linkp.start_node.demand_coeff + linkp.start_node.emitter_coeff
        aq = 1
        bq = -a/g*k/A
        # cq = a/g *V1 - a/g*f*dt/(2.*D)*V1*abs(V1) - H1 - g/a*dt*V1*linkp.theta + elev
        cq = a/g *V1 - a/g*J - H1 - g/a*dt*V1*linkp.theta + elev
        # solve the quadratic equation
        delta = bq**2. - 4.*aq*cq
        if delta >= 0:
            HP = (-bq - np.sqrt(delta))/(2*aq)
            HP = HP**2. + elev
        elif delta > -1.0e-7 and delta <0 :
            HP = (-bq)/(2*aq)
            HP = HP**2. +elev
        else:
            HP = (-bq)/(2*aq)
            HP = HP**2. +elev
            warnings.warn("""The quadratic equation has no real solution (dead end).
                            The results might not be accurate.""")
        VP = V1 - g/a*H1 - f*dt/(2.*D)*V1*abs(V1) + g/a*HP - g/a*dt*V1*linkp.theta
    else : # dead end is the end node of a pipe
        k = linkp.end_node.demand_coeff + linkp.end_node.emitter_coeff
        aq = 1
        bq = a/g*k/A
        # cq = -a/g *V1 + a/g*f*dt/(2.*D)*V1*abs(V1) - H1 - g/a*dt*V1*linkp.theta + elev
        cq = -a/g *V1 + a/g*J - H1 - g/a*dt*V1*linkp.theta + elev
        # solve the quadratic equation
        delta = bq**2. - 4.*aq*cq
        if delta >= 0:
            HP = (-bq + np.sqrt(delta))/(2*aq)
            HP = HP**2. + elev
        elif delta > -1.0e-7 and delta <0 :
            HP = (-bq)/(2*aq)
            HP = HP**2. + elev
        else:
            HP = (-bq)/(2*aq)
            HP = HP**2. + elev
            warnings.warn("The quadratic equation has no real solution (dead end).\
The results might not be accurate.")
        VP = V1 + g/a *H1 - f*dt/(2.*D)*V1*abs(V1) - g/a*HP + g/a*dt*V1*linkp.theta
    return HP,VP

def rev_end( H2, V2, H, nn, a, g, f, D, dt,
            KD, friction, dVdx2, dVdt2):
    """Reservoir/ Tank boundary MOC calculation

    Parameters
    ----------
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    H : float
        Head of the reservoir/tank
    nn : int
        The index of the calculation node
    a : float
        Wave speed at the valve end
    g : float
        Gravity acceleration
    f : float
        friction factor of the current pipe
    D : float
        diameter of the current pipe
    dt : float
        Time step
    KD : float
        relative roughness height
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """
    J = cal_friction(friction, f, D, V2, KD, dt, dVdt2, dVdx2, a, g )
    if nn == 0 :
        VP = V2 + g/a*(H - H2) - J
        HP = H
    else:
        VP = V2 - g/a*(H - H2) - J
        HP = H
    return HP, VP

def add_leakage(emitter_coef, block_per, link1, link2, elev,
                 H1, V1, H2, V2, dt, g, nn, s1, s2,
                 friction, dVdx1=0, dVdx2=0, dVdt1=0, dVdt2=0):
    r"""Leakage Node MOC calculation

    Parameters
    ----------
    emitter_coef : float
        float, optional
        Required if leak_loc is defined
        The leakage coefficient of the leakage
        .. math:: Q_leak = leak_A  [ m^3/s/(m H20)^(1/2)] * \sqrt(H)
    link1 : object
        Pipe object of C+ charateristics curve
    link2 : object
        Pipe object of C- charateristics curve
    H1 : list
        List of the head of C+ charateristics curve
    V1 : list
        List of the velocity of C+ charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    nn : int
        The index of the calculation node
    s1 : list
        List of signs that represent the direction of the flow
        in C+ charateristics curve
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """

    emitter_coef = emitter_coef  # m^3/s//(m H2O)^(1/2)

    try :
        list(link1)
    except:
        link1 = [link1]
        V1 = [V1] ; H1 = [H1]
        dVdx1 = [dVdx1]; dVdt1 = [dVdt1]
    try :
        list(link2)
    except:
        link2 = [link2]
        V2 = [V2] ; H2 = [H2]
        dVdx2 = [dVdx2]; dVdt2 = [dVdt2]

    A1, A2, C1, C2 = cal_Cs(link1, link2, H1, V1, H2, V2, s1, s2, g, dt,
            friction, dVdx1, dVdx2, dVdt1, dVdt2)

    a = np.dot(C1[:,0], A1) + np.dot(C2[:,0],A2)
    b = np.dot(C1[:,1], A1) + (1-block_per)*np.dot(C2[:,1],A2)
    # parameters of the quadratic polynomial
    # a1 = b**2.
    # b1 = -(2.*a*b +emitter_coef**2)
    # c1 = a**2.
    a1 = b**2
    b1 = -2*a*b - emitter_coef**2.
    c1 = a**2 + emitter_coef**2.*elev

    # solve the quadratic equation
    delta = b1**2 - 4*a1*c1
    if delta >= 0:
        HP = (-b1 - np.sqrt(delta))/(2*a1)
    elif delta > -1.0e-7 and delta <0 :
        HP = (-b1)/(2*a1)
    else:
        HP = (-b1)/(2*a1)
        warnings.warn('Error: The quadratic equation has no real solution (leakage)')

    if nn == 0:  # pipe start
        VP = np.float64(-C2[:,0]+ C2[:,1]*HP)
    else:        # pipe end
        VP = np.float64(C1[:,0] - C1[:,1]*HP)
    return HP, VP


def surge_tank(tank, link1, link2, H1, V1, H2, V2, dt, g, nn, s1, s2,
                friction, dVdx1, dVdx2, dVdt1, dVdt2):

    """Surge tank node MOC calculation

    Parameters
    ----------
    tank : int
        tank shape parameters
        [As, z, Qs]
            As : cross-sectional area of the surge tank
            z : water level in the surge tank at previous time step
            Qs : water flow into the tank at last time step
    link1 : object
        Pipe object of C+ charateristics curve
    link2 : object
        Pipe object of C- charateristics curve
    H1 : list
        List of the head of C+ charateristics curve
    V1 : list
        List of the velocity of C+ charateristics curve
    H2 : list
        List of the head of C- charateristics curve
    V2 : list
        List of the velocity of C- charateristics curve
    dt : float
        Time step
    g : float
        Gravity acceleration
    nn : int
        The index of the calculation node
    s1 : list
        List of signs that represent the direction of the flow
        in C+ charateristics curve
    s2 : list
        List of signs that represent the direction of the flow
        in C- charateristics curve
    friction : str
        friction model, e.g., 'steady', 'quasi-steady', 'unsteady',
        by default 'steady'
    dVdx1 : list
        List of convective instantaneous acceleration on the
        C+ characteristic curve
    dVdx2 : list
        List of convective instantaneous acceleration on the
        C- characteristic curve
    dVdt1 : list
        List of local instantaneous acceleration on the
        C+ characteristic curve
    dVdt2 : list
        List of local instantaneous acceleration on the
        C- characteristic curve
    """

    try :
        list(link1)
    except:
        link1 = [link1]
        V1 = [V1] ; H1 = [H1]
        dVdx1 = [dVdx1]; dVdt1 = [dVdt1]
    try :
        list(link2)
    except:
        link2 = [link2]
        V2 = [V2] ; H2 = [H2]
        dVdx2 = [dVdx2]; dVdt2 = [dVdt2]

    A1, A2, C1, C2 = cal_Cs(link1, link2, H1, V1, H2, V2, s1, s2, g, dt,
            friction, dVdx1, dVdx2, dVdt1, dVdt2)

    As, z, Qs = tank
    at = 2.* As/dt

    HP = ((np.dot(C1[:,0], A1) + np.dot(C2[:,0],A2) + at*z + Qs ) /
         (np.dot(C1[:,1], A1) + np.dot(C2[:,1],A2) + at))

    VP2 = -C2[:,0]+ C2[:,1]*HP
    VP1 = C1[:,0] - C1[:,1]*HP
    QPs = (np.sum(np.array(VP1)*np.array(A1)) -
            np.sum(np.array(VP2)*np.array(A2)))

    if nn == 0:  # pipe start
        VP =np.float64(VP2)
    else:        # pipe end
        VP = np.float64(VP1)
    return HP, VP, QPs