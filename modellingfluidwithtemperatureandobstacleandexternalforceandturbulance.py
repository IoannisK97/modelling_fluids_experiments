import numpy as np
import scipy.sparse.linalg as splinalg
from scipy import interpolate
import matplotlib.pyplot as plt

# Optional
import cmasher as cmr
from tqdm import tqdm

DOMAIN_SIZE = 1.0
N_POINTS = 41
N_TIME_STEPS = 100
TIME_STEP_LENGTH = 0.1

KINEMATIC_VISCOSITY = 0.0001
TEMPERATURE_DIFFUSIVITY = 0.0001
SMAGORINSKY_CONSTANT = 0.1  # Typical value
element_length = DOMAIN_SIZE / (N_POINTS - 1)


MAX_ITER_CG = None


def forcing_function(time, point):
    time_decay = np.maximum(
        2.0 - 0.5 * time,
        0.0,
    )

    forced_value = (
            time_decay
            *
            np.where(
                (
                        (point[0] > 0.4)
                        &
                        (point[0] < 0.6)
                        &
                        (point[1] > 0.1)
                        &
                        (point[1] < 0.3)
                ),
                np.array([0.0, 1.0]),
                np.array([0.0, 0.0]),
            )
    )

    return forced_value

def external_force(time, coordinates):
    
    force_y = -0.1 * np.sin(2 * np.pi * time / 10)  # y direction
    force_x = 0.1 * np.sin(2 * np.pi * coordinates[..., 1])  #x direction

    force_field = np.zeros(coordinates.shape)
    force_field[..., 0] = force_x  # x-component of force
    force_field[..., 1] = force_y  # y-component of force

    return force_field


def main():
    element_length = DOMAIN_SIZE / (N_POINTS - 1)
    scalar_shape = (N_POINTS, N_POINTS)
    scalar_dof = N_POINTS ** 2
    vector_shape = (N_POINTS, N_POINTS, 2)
    vector_dof = N_POINTS ** 2 * 2

    

    x = np.linspace(0.0, DOMAIN_SIZE, N_POINTS)
    y = np.linspace(0.0, DOMAIN_SIZE, N_POINTS)

    # Using "ij" indexing makes the differential operators more logical.
    
    X, Y = np.meshgrid(x, y, indexing="ij")

    obstacle_center = np.array([0.5, 0.5])  # Center of the domain
    obstacle_radius = 0.1  # Radius of the circular obstacle
    obstacle_mask = (X - obstacle_center[0])**2 + (Y - obstacle_center[1])**2 < obstacle_radius**2


    coordinates = np.concatenate(
        (
            X[..., np.newaxis],
            Y[..., np.newaxis],
        ),
        axis=-1,
    )

    forcing_function_vectorized = np.vectorize(
        pyfunc=forcing_function,
        signature="(),(d)->(d)",
    )


    def compute_strain_rate(velocity_field):
        """
        Compute the strain rate tensor magnitude |S| = sqrt(2 S_ij S_ij).
        """
        du_dx = partial_derivative_x(velocity_field[..., 0])
        dv_dy = partial_derivative_y(velocity_field[..., 1])
        du_dy = partial_derivative_y(velocity_field[..., 0])
        dv_dx = partial_derivative_x(velocity_field[..., 1])

        # Strain rate tensor components
        S11 = du_dx
        S22 = dv_dy
        S12 = 0.5 * (du_dy + dv_dx)

        # Magnitude of the strain rate tensor
        strain_rate_magnitude = np.sqrt(2 * (S11**2 + S22**2 + 2 * S12**2))

        return strain_rate_magnitude

    def compute_turbulent_viscosity(velocity_field):
        """
        Compute the turbulent viscosity ν_t based on the Smagorinsky model.
        """
        strain_rate_magnitude = compute_strain_rate(velocity_field)
        turbulent_viscosity = (SMAGORINSKY_CONSTANT * element_length)**2 * strain_rate_magnitude
        return turbulent_viscosity

    def diffusion_operator_turbulent(vector_field_flattened):
        """
        Diffusion operator with turbulent viscosity included.
        """
        vector_field = vector_field_flattened.reshape(vector_shape)

        # Compute turbulent viscosity ν_t
        turbulent_viscosity = compute_turbulent_viscosity(vector_field)

        # Add turbulent viscosity to kinematic viscosity
        effective_viscosity = KINEMATIC_VISCOSITY + turbulent_viscosity

        # Diffusion term with spatially varying viscosity
        diffused = np.zeros_like(vector_field)
        for i in range(2):  # For both velocity components (u, v)
            diffused[..., i] = (
                vector_field[..., i]
                - TIME_STEP_LENGTH * divergence(effective_viscosity[..., np.newaxis] * gradient(vector_field[..., i]))
            )

        return diffused.flatten()

   


    def partial_derivative_x(field):
        diff = np.zeros_like(field)

        diff[1:-1, 1:-1] = (
                (
                        field[2:, 1:-1]
                        -
                        field[0:-2, 1:-1]
                ) / (
                        2 * element_length
                )
        )

        return diff

    def partial_derivative_y(field):
        diff = np.zeros_like(field)

        diff[1:-1, 1:-1] = (
                (
                        field[1:-1, 2:]
                        -
                        field[1:-1, 0:-2]
                ) / (
                        2 * element_length
                )
        )

        return diff

    def laplace(field):
        diff = np.zeros_like(field)

        diff[1:-1, 1:-1] = (
                (
                        field[0:-2, 1:-1]
                        +
                        field[1:-1, 0:-2]
                        - 4 *
                        field[1:-1, 1:-1]
                        +
                        field[2:, 1:-1]
                        +
                        field[1:-1, 2:]
                ) / (
                        element_length ** 2
                )
        )

        return diff

    def divergence(vector_field):
        divergence_applied = (
                partial_derivative_x(vector_field[..., 0])
                +
                partial_derivative_y(vector_field[..., 1])
        )

        return divergence_applied

    def gradient(field):
        gradient_applied = np.concatenate(
            (
                partial_derivative_x(field)[..., np.newaxis],
                partial_derivative_y(field)[..., np.newaxis],
            ),
            axis=-1,
        )

        return gradient_applied

    def curl_2d(vector_field):
        curl_applied = (
                partial_derivative_x(vector_field[..., 1])
                -
                partial_derivative_y(vector_field[..., 0])
        )

        return curl_applied

    def advect(field, vector_field):
        backtraced_positions = np.clip(
            (
                    coordinates
                    -
                    TIME_STEP_LENGTH
                    *
                    vector_field
            ),
            0.0,
            DOMAIN_SIZE,
        )

        advected_field = interpolate.interpn(
            points=(x, y),
            values=field,
            xi=backtraced_positions,
        )

        return advected_field
    
    def temperature_step(temperature, velocity_field, source):
        # Advection
        temperature_advected = advect(
            field=temperature,
            vector_field=velocity_field,
        )

        # Diffusion
        def temperature_diffusion_operator(temp_flattened):
            temp = temp_flattened.reshape(scalar_shape)
            return (temp - TEMPERATURE_DIFFUSIVITY * TIME_STEP_LENGTH * laplace(temp)).flatten()

        temperature_diffused = splinalg.cg(
            A=splinalg.LinearOperator(
                shape=(scalar_dof, scalar_dof),
                matvec=temperature_diffusion_operator,
            ),
            b=temperature_advected.flatten(),
        )[0].reshape(scalar_shape)

        # Add Source
        temperature_next = temperature_diffused + TIME_STEP_LENGTH * source
        return temperature_next

    def diffusion_operator(vector_field_flattened):
        vector_field = vector_field_flattened.reshape(vector_shape)

        diffusion_applied = (
                vector_field
                -
                KINEMATIC_VISCOSITY
                *
                TIME_STEP_LENGTH
                *
                laplace(vector_field)
        )

        return diffusion_applied.flatten()

    def poisson_operator(field_flattened):
        field = field_flattened.reshape(scalar_shape)

        poisson_applied = laplace(field)

        return poisson_applied.flatten()

    plt.style.use("dark_background")
    plt.figure(figsize=(5, 5), dpi=160)

    velocities_prev = np.zeros(vector_shape)

    temperature_prev = np.zeros(scalar_shape)
    temperature_source = np.exp(-((X - 0.5)**2 + (Y - 0.5)**2) / 0.01)

    time_current = 0.0
    for i in tqdm(range(N_TIME_STEPS)):
        time_current += TIME_STEP_LENGTH

        forces = forcing_function_vectorized(
            time_current,
            coordinates,
        )

        external_forces = external_force(time_current, coordinates)

        # (1) Apply Forces
        velocities_forces_applied = (
                velocities_prev
                +
                TIME_STEP_LENGTH
                *
                (forces + external_forces)
        )

        # (2) Nonlinear convection (=self-advection)
        velocities_advected = advect(
            field=velocities_forces_applied,
            vector_field=velocities_forces_applied,
        )

        # (3) Diffuse
        velocities_diffused = splinalg.cg(
            A=splinalg.LinearOperator(
                shape=(vector_dof, vector_dof),
                matvec=diffusion_operator_turbulent,
            ),
            b=velocities_advected.flatten(),
            maxiter=MAX_ITER_CG,
        )[0].reshape(vector_shape)

        # (4.1) Compute a pressure correction
        pressure = splinalg.cg(
            A=splinalg.LinearOperator(
                shape=(scalar_dof, scalar_dof),
                matvec=poisson_operator,
            ),
            b=divergence(velocities_diffused).flatten(),
            maxiter=MAX_ITER_CG,
        )[0].reshape(scalar_shape)

        # (4.2) Correct the velocities to be incompressible
        velocities_projected = (
                velocities_diffused
                -
                gradient(pressure)
        )

        velocities_projected[obstacle_mask, :] = 0
        temperature_prev = temperature_step(
            temperature=temperature_prev,
            velocity_field=velocities_projected,
            source=temperature_source,
        )


        #temperature_prev[obstacle_mask] = 0.0 #heat sink
        #temperature_prev[obstacle_mask] = 1.0 #heat source

        temperature_prev[obstacle_mask] = 0.5 

        # Advance to next time step
        velocities_prev = velocities_projected

        # Plot
        curl = curl_2d(velocities_projected)
        plt.contourf(
            X,
            Y,
            curl,
            cmap=cmr.redshift,
            levels=100,
            alpha=0.7,  # Add transparency to curl
        )
        plt.contourf(
            X,
            Y,
            temperature_prev,
            cmap='hot',
            levels=100,
            alpha=0.5,  # Add transparency to temperature
        )

        plt.contour(
            X,
            Y,
            obstacle_mask,
            colors='white',
            linewidths=1.5,
        )
        plt.quiver(
            X,
            Y,
            velocities_projected[..., 0],
            velocities_projected[..., 1],
            color="dimgray",
        )
        plt.quiver(
        X,
        Y,
        external_forces[..., 0],
        external_forces[..., 1],
        color="cyan",
        scale=5,
        label="External Force",
         )
        plt.draw()
        plt.pause(0.0001)
        plt.clf()

    plt.show()


if __name__ == "__main__":
    main()