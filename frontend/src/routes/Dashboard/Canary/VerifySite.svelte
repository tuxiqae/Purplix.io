<script lang="ts">
  import { onMount } from "svelte";
  import { navigate } from "svelte-navigator";

  import PageLoading from "../../../components/PageLoading.svelte";
  import apiClient from "../../../lib/apiClient";
  import { goToCanary } from "../../../lib/canary";
  import type { CanaryModel } from "../../../lib/client";

  export let domainName: string;

  let canary: CanaryModel;
  let verifyCode = "";
  let isLoading = true;
  let domainVerifyFailed = false;

  let domainVerifying = false;

  async function verifyDomain() {
    domainVerifying = true;
    try {
      await apiClient.canary.controllersCanaryDomainVerifyVerify(domainName);
      domainVerifyFailed = false;

      goToCanary(canary);
    } catch (error) {
      domainVerifyFailed = true;
    }

    domainVerifying = false;
  }

  onMount(async () => {
    try {
      canary = await apiClient.canary.controllersCanaryDomainGetCanary(
        domainName
      );
      verifyCode = canary.domain_verification.code_prefixed as string;
    } catch (error) {
      navigate("/dashboard", { replace: true });
    }

    if (canary.hex_color) await ui("theme", `#${canary.hex_color}`);

    if (canary.domain_verification.completed) {
      goToCanary(canary);
    }

    isLoading = false;
  });
</script>

{#if !isLoading}
  {#if domainVerifyFailed}
    <article class="primary">
      <h6>Unable to verify domain</h6>
      <p>
        Remember that DNS propagation can take anywhere from a few minutes to
        several hours.
      </p>
    </article>
  {/if}

  <h3>Verify {canary.domain}</h3>
  <article>
    <h6>Step 1</h6>
    <p>Log in to your DNS provider's control panel or dashboard.</p>

    <h6>Step 2</h6>
    <p>
      Look for the option to add a new DNS record and select "TXT" as the record
      type.
    </p>
    <p>In the "Name" or "Host" field, enter "@" or the subdomain.</p>

    <h6>Step 3</h6>
    <p>In the "Value" or "Data" field, enter the following.</p>

    <nav>
      <div class="field border">
        <input type="text" readonly value={verifyCode} />
      </div>
      <button
        class="square round large"
        on:click={async () => {
          await navigator.clipboard.writeText(verifyCode);
        }}
      >
        <i>content_copy</i>
      </button>
    </nav>

    <h6>Step 4</h6>
    <p>
      Please wait for DNS propagation to occur, which can take anywhere from a
      few minutes to several hours.
    </p>
    <p>
      {import.meta.env.VITE_SITE_NAME} will check periodically in the background.
      Expect an email once validation is successful.
    </p>

    <div class="right-align" style="margin-top: 1em;">
      {#if domainVerifying}
        <span class="loader medium" />
      {:else}
        <button on:click={verifyDomain}>
          <i>travel_explore</i>
          <span>Validate domain</span>
        </button>
      {/if}
    </div>
  </article>
{:else}
  <PageLoading />
{/if}
